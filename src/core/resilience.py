"""
src/core/resilience.py
Resilience utilities: Exponential backoff with jitter, timeouts, and error taxonomy.
"""
import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorTaxonomy:
    """Standardized Error Taxonomy for TalentForge AI."""
    E101_RATE_LIMIT_EXCEEDED = "E101: Rate limit exceeded (HTTP 429). Backoff triggered."
    E102_VALIDATION_FAILURE = "E102: Structured Pydantic validation failed on LLM response."
    E103_LLM_TIMEOUT = "E103: LLM inference exceeded deadline timeout."
    E104_HALLUCINATION_DETECTED = "E104: Validator Agent detected ungrounded claims."
    E105_CORRUPT_OR_MISSING_FILE = "E105: Resume file is empty, missing, or unparseable."
    E106_DATABASE_ERROR = "E106: Database query or transaction failed."


class ResilienceException(Exception):
    """Base exception for resilience failures."""
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}


def exponential_backoff_retry(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 5.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    Synchronous decorator for exponential backoff with full jitter.
    Logs each retry attempt with latency and error reason.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            delay = initial_delay
            last_exception = None

            while attempt < max_retries:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    # Do not retry on explicit cancellation or fatal domain errors
                    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                        raise
                    
                    if attempt >= max_retries:
                        logger.error(
                            "Max retries (%d) exceeded for %s. Last error: %s",
                            max_retries, func.__name__, exc
                        )
                        break

                    jitter = random.uniform(0.8, 1.2)
                    sleep_time = min(max_delay, delay * jitter)
                    logger.warning(
                        "Attempt %d failed for %s with %s. Retrying in %.2fs...",
                        attempt, func.__name__, exc, sleep_time
                    )
                    time.sleep(sleep_time)
                    delay *= backoff_factor

            raise ResilienceException(
                code=ErrorTaxonomy.E101_RATE_LIMIT_EXCEEDED,
                message=f"Function {func.__name__} failed after {max_retries} attempts: {last_exception}",
                details={"attempts": attempt, "last_error": str(last_exception)},
            ) from last_exception

        return wrapper
    return decorator


async def with_async_timeout(
    coro_or_func: Any,
    timeout_seconds: float = 15.0,
    fallback_value: Any = None,
    error_code: str = ErrorTaxonomy.E103_LLM_TIMEOUT,
) -> Any:
    """
    Executes an async task within a strict timeout deadline.
    Returns fallback_value if timeout is exceeded instead of crashing.
    """
    try:
        return await asyncio.wait_for(coro_or_func, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(
            "Async operation timed out after %.2fs. Code=%s. Returning fallback.",
            timeout_seconds, error_code
        )
        if fallback_value is not None:
            return fallback_value
        raise ResilienceException(
            code=error_code,
            message=f"Operation timed out after {timeout_seconds} seconds",
            details={"timeout_seconds": timeout_seconds},
        )

