import os
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Configuration settings loaded from environment variables or .env file."""

    # Example settings – extend as needed
    DATABASE_URL: str = Field(default="sqlite:///./app.db", env="DATABASE_URL")
    DEBUG: bool = Field(default=False, env="DEBUG")

    @classmethod
    def load_env(cls):
        # Load .env if present – Pydantic BaseSettings does this automatically on init
        # Here we just force creation to trigger loading
        return cls()
