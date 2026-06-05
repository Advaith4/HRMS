import logging
from groq import Groq
from src.services.llm_router import key_manager

logger = logging.getLogger(__name__)

def _get_healthy_client() -> Groq:
    """Always return a fresh client if needed, to respect router changes."""
    api_key = key_manager.get_healthy_key()
    if not api_key:
        raise RuntimeError("No healthy GROQ_API_KEY available for transcription.")
    return Groq(api_key=api_key)

def transcribe_audio(file_path: str) -> str:
    client = _get_healthy_client()
    model = "whisper-large-v3"

    try:
        with open(file_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model=model,
                file=f,
                response_format="text",
                language="en",
            )
        return transcription.strip()
    except Exception as e:
        logger.warning("whisper-large-v3 failed: %s. Trying distil-whisper-large-v3-en...", e)
        try:
            with open(file_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="distil-whisper-large-v3-en",
                    file=f,
                    response_format="text",
                    language="en",
                )
            return transcription.strip()
        except Exception as e2:
            logger.error("Transcription failed with fallback model: %s", e2)
            raise RuntimeError(f"Transcription failed: {e2}") from e2
