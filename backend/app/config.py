import os
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    try:
        from pydantic import BaseSettings, Field  # type: ignore
    except ImportError:
        from pydantic import BaseModel as BaseSettings, Field  # type: ignore

class Settings(BaseSettings):
    """Configuration settings loaded from environment variables or .env file."""

    DATABASE_URL: str = Field(default=os.getenv("DATABASE_URL", "sqlite:///./app.db"))
    DEBUG: bool = Field(default=os.getenv("DEBUG", "false").lower() in ("true", "1"))

    @classmethod
    def load_env(cls):
        # Load .env if present – Pydantic BaseSettings does this automatically on init
        # Here we just force creation to trigger loading
        return cls()
