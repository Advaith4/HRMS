import os
import time
import logging
from threading import Lock
from crewai import LLM
import litellm

logger = logging.getLogger(__name__)

# Global Litellm Configuration
litellm.drop_params = True
_original_completion = litellm.completion

class APIKeyManager:
    """Manages a pool of API keys, tracks health and rate limits."""
    def __init__(self):
        self.keys = []
        self.health = {}
        self.cooldown_until = {}
        self.lock = Lock()
        self._load_keys()

    def _load_keys(self):
        # Support dynamic GROQ keys like GROQ_API_KEY, GROQ_API_KEY_1, GROQ_API_KEY_2, etc.
        for k, v in os.environ.items():
            if k.startswith("GROQ_API_KEY") and v.strip():
                if v not in self.keys:
                    self.keys.append(v)
                    self.health[v] = True
                    self.cooldown_until[v] = 0.0
        
        if not self.keys:
            logger.warning("No GROQ_API_KEY found in environment.")
        else:
            logger.info(f"Loaded {len(self.keys)} Groq API keys.")

    def get_healthy_key(self) -> str:
        with self.lock:
            now = time.time()
            # Restore healthy state for cooled down keys
            for key in self.keys:
                if now >= self.cooldown_until.get(key, 0.0):
                    self.health[key] = True
            
            healthy = [k for k in self.keys if self.health.get(k, False)]
            if not healthy:
                logger.warning("All keys are currently exhausted or on cooldown. Falling back to primary key.")
                return self.keys[0] if self.keys else ""
            return healthy[0]

    def mark_unhealthy(self, key: str, cooldown_seconds: float = 60.0):
        if not key:
            return
        with self.lock:
            self.health[key] = False
            self.cooldown_until[key] = time.time() + cooldown_seconds
            logger.warning(f"Key ending with ...{key[-4:]} marked unhealthy. Cooldown for {cooldown_seconds}s.")

key_manager = APIKeyManager()

def _routed_completion(*args, **kwargs):
    """
    Intercepts litellm.completion to inject healthy keys and handle rate limit retries transparently.
    Also removes incompatible parameters like 'cache_breakpoint'.
    """
    if kwargs.get("messages"):
        for msg in kwargs["messages"]:
            msg.pop("cache_breakpoint", None)

    max_retries = max(1, len(key_manager.keys))
    last_exc = None

    for attempt in range(max_retries):
        key = key_manager.get_healthy_key()
        if key:
            kwargs["api_key"] = key
            
        try:
            return _original_completion(*args, **kwargs)
        except Exception as e:
            last_exc = e
            err_str = str(e).lower()
            if "rate limit" in err_str or "429" in err_str or "decommission" in err_str:
                logger.warning(f"Rate limit or 429 hit on key ...{key[-4:] if key else 'None'}. Marking unhealthy.")
                key_manager.mark_unhealthy(key, cooldown_seconds=60.0)
            else:
                # If it's a non-rate-limit error (e.g., bad request, auth error), just raise it immediately
                raise e

    logger.error("All available LLM keys exhausted or failed due to rate limits.")
    raise last_exc

# Apply global monkey-patch
litellm.completion = _routed_completion

def get_llm(temperature=0.5, provider="groq", model=None):
    """
    Returns a configured CrewAI LLM using the centralized router logic.
    Provider abstraction added for future NVIDIA NIM support.
    """
    if provider == "groq":
        model_name = model or "groq/llama-3.1-8b-instant"
        if not model_name.startswith("groq/"):
            model_name = f"groq/{model_name}"
        return LLM(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY", "dummy"), # Actual api_key is injected in _routed_completion
            timeout=25.0,
        )
    elif provider == "nvidia_nim":
        # Placeholder for NVIDIA NIM integration
        raise NotImplementedError("NVIDIA NIM support not yet implemented.")
    else:
        raise ValueError(f"Unknown provider: {provider}")
