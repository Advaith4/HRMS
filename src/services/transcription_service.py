import logging
import os
import time
import json
from groq import Groq
from src.services.llm_router import key_manager

logger = logging.getLogger(__name__)

PROMPT_ECHO_MARKERS = (
    "avoid hallucinations and noise",
    "candidate answer to interview question",
)
MIN_AUDIO_BYTES = 1200


def _safe_raw_response(response) -> str:
    if response is None:
        return "None"
    try:
        if hasattr(response, "model_dump"):
            return json.dumps(response.model_dump(), ensure_ascii=True, default=str)[:4000]
        if hasattr(response, "dict"):
            return json.dumps(response.dict(), ensure_ascii=True, default=str)[:4000]
    except Exception:
        pass
    return str(response)[:4000]

def _get_healthy_client() -> Groq:
    """Always return a fresh client if needed, to respect router changes."""
    api_key = key_manager.get_healthy_key()
    if not api_key:
        raise RuntimeError("No healthy GROQ_API_KEY available for transcription.")
    return Groq(api_key=api_key)

def _metadata_from_response(response, processing_time_ms: int, model: str, file_path: str) -> dict:
    if isinstance(response, dict):
        transcript = str(response.get("text") or "").strip()
        duration = response.get("duration")
        language = response.get("language")
        segments = response.get("segments") or []
    else:
        transcript = (getattr(response, "text", None) or str(response) or "").strip()
        duration = getattr(response, "duration", None)
        language = getattr(response, "language", None)
        segments = getattr(response, "segments", None) or []
    no_speech_probs = []
    for segment in segments:
        value = getattr(segment, "no_speech_prob", None)
        if value is None and isinstance(segment, dict):
            value = segment.get("no_speech_prob")
        if isinstance(value, (int, float)):
            no_speech_probs.append(float(value))
    confidence = None
    if no_speech_probs:
        confidence = round(max(0.0, min(1.0, 1.0 - (sum(no_speech_probs) / len(no_speech_probs)))), 3)

    return {
        "transcript": transcript,
        "confidence": confidence,
        "duration": duration,
        "processing_time_ms": processing_time_ms,
        "model": model,
        "language": language,
        "file_size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else None,
    }


def _validate_transcript(metadata: dict, raw_response: str, mime_type: str | None = None, client_duration_seconds: float | None = None) -> dict:
    transcript = str(metadata.get("transcript") or "").strip()
    normalized = transcript.lower()
    if any(marker in normalized for marker in PROMPT_ECHO_MARKERS):
        logger.error(
            "transcription_rejected reason=prompt_echo model=%s file_size_bytes=%s mime_type=%s duration_seconds=%s transcript=%r raw_response=%s",
            metadata.get("model"),
            metadata.get("file_size_bytes"),
            mime_type,
            metadata.get("duration") or client_duration_seconds,
            transcript,
            raw_response,
        )
        raise RuntimeError("Transcription returned prompt text instead of speech. Please re-record with audible speech.")
    return metadata


def transcribe_audio_metadata(
    file_path: str,
    mime_type: str | None = None,
    client_duration_seconds: float | None = None,
    request_cache_key: str | None = None,
) -> dict:
    client = _get_healthy_client()
    model = "whisper-large-v3"
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    cache_key = request_cache_key or f"{file_size}:{int(os.path.getmtime(file_path)) if os.path.exists(file_path) else 0}"
    logger.info(
        "transcription_cache_lookup cache_key=%s cache_hit=false file_size_bytes=%s mime_type=%s duration_seconds=%s",
        cache_key,
        file_size,
        mime_type,
        client_duration_seconds,
    )
    if file_size < MIN_AUDIO_BYTES:
        logger.warning(
            "transcription_small_file_continue cache_key=%s file_size_bytes=%s min_audio_bytes=%s mime_type=%s duration_seconds=%s rejection_disabled=true",
            cache_key,
            file_size,
            MIN_AUDIO_BYTES,
            mime_type,
            client_duration_seconds,
        )

    max_retries = 3
    for attempt in range(max_retries):
        started = time.perf_counter()
        try:
            with open(file_path, "rb") as f:
                logger.info(
                    "whisper_request_start model=%s attempt=%s file_size_bytes=%s mime_type=%s duration_seconds=%s cache_key=%s",
                    model,
                    attempt + 1,
                    file_size,
                    mime_type,
                    client_duration_seconds,
                    cache_key,
                )
                transcription = client.audio.transcriptions.create(
                    model=model,
                    file=f,
                    response_format="verbose_json",
                    temperature=0.0,
                )
            raw_response = _safe_raw_response(transcription)
            logger.info("transcription_raw_response model=%s attempt=%s raw_response=%s", model, attempt + 1, raw_response)
            metadata = _metadata_from_response(
                transcription,
                int((time.perf_counter() - started) * 1000),
                model,
                file_path,
            )
            metadata = _validate_transcript(metadata, raw_response, mime_type, client_duration_seconds)
            logger.info(
                "transcription_completed model=%s language=%s duration=%s confidence=%s processing_time_ms=%s file_size_bytes=%s mime_type=%s cache_key=%s",
                metadata["model"],
                metadata["language"],
                metadata["duration"],
                metadata["confidence"],
                metadata["processing_time_ms"],
                metadata["file_size_bytes"],
                mime_type,
                cache_key,
            )
            return metadata
        except Exception as e:
            logger.warning(
                "transcription_attempt_failed model=%s attempt=%d/%d file_size_bytes=%s mime_type=%s duration_seconds=%s error=%s",
                model,
                attempt + 1,
                max_retries,
                os.path.getsize(file_path) if os.path.exists(file_path) else None,
                mime_type,
                client_duration_seconds,
                e,
            )
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                fallback_model = "whisper-large-v3-turbo"
                logger.warning("transcription_fallback_start model=%s", fallback_model)
                try:
                    fallback_started = time.perf_counter()
                    with open(file_path, "rb") as f:
                        logger.info(
                            "whisper_request_start model=%s attempt=fallback file_size_bytes=%s mime_type=%s duration_seconds=%s cache_key=%s",
                            fallback_model,
                            file_size,
                            mime_type,
                            client_duration_seconds,
                            cache_key,
                        )
                        transcription = client.audio.transcriptions.create(
                            model=fallback_model,
                            file=f,
                            response_format="verbose_json",
                            temperature=0.0,
                        )
                    raw_response = _safe_raw_response(transcription)
                    logger.info("transcription_raw_response model=%s attempt=fallback raw_response=%s", fallback_model, raw_response)
                    return _validate_transcript(_metadata_from_response(
                        transcription,
                        int((time.perf_counter() - fallback_started) * 1000),
                        fallback_model,
                        file_path,
                    ), raw_response, mime_type, client_duration_seconds)
                except Exception as e2:
                    logger.error(
                        "transcription_rejected reason=whisper_failure fallback_model=%s file_size_bytes=%s mime_type=%s duration_seconds=%s error=%s",
                        fallback_model,
                        file_size,
                        mime_type,
                        client_duration_seconds,
                        e2,
                        exc_info=True,
                    )
                    raise RuntimeError(f"Transcription failed: {e2}") from e2


def transcribe_audio(file_path: str) -> str:
    return transcribe_audio_metadata(file_path)["transcript"]
