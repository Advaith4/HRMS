from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # --- App ---
    APP_NAME: str = "TalentForge AI"
    DEBUG: bool = False

    # --- AI Keys ---
    GROQ_API_KEY: str = ""
    MODEL_NAME: str = "llama-3.1-8b-instant"

    # --- Database ---
    DATABASE_URL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    PGSSLMODE: str = "require"
    DATABASE_CONNECT_TIMEOUT: int = 10
    AUTO_CREATE_DB_SCHEMA: bool = True

    # --- JWT ---
    SECRET_KEY: str = "change-me-in-production-min-32-chars!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    # --- DB pool tuning (override via env) ---
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 15

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False
        return False

    @model_validator(mode="after")
    def validate_production_secret(self):
        weak_values = {
            "",
            "change-me-in-production-min-32-chars!!",
            "replace-with-a-random-32-plus-character-secret",
        }
        database_url = (self.DATABASE_URL or "").strip().lower()
        sqlite_mode = database_url.startswith("sqlite")
        explicit_test_secret = self.SECRET_KEY.startswith("test-secret-key-")
        if not self.DEBUG and not sqlite_mode:
            if not explicit_test_secret and (self.SECRET_KEY in weak_values or len(self.SECRET_KEY.strip()) < 32):
                raise RuntimeError(
                    "SECRET_KEY must be set to a random 32+ character value for non-test deployments."
                )
        return self

settings = Settings()
