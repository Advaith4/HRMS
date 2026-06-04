import logging
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

_client = None

def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = Groq(api_key=api_key)
    return _client


def transcribe_audio(file_path: str) -> str:
    client = _get_client()
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
