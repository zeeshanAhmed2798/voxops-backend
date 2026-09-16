"""
app/core/config.py
==================
Central configuration loader for VoxOps backend.

HOW IT WORKS:
- Pydantic's BaseSettings reads values from the .env file automatically.
- If a variable is missing from .env and has no default, startup will FAIL clearly.
- We access settings everywhere via: from app.core.config import settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings loaded from environment variables.
    Add new config values here — never hardcode them in other files.
    """

    # --- Database ---
    DATABASE_URL: str  # e.g. postgresql+psycopg://user:pass@localhost:5432/voxops

    # --- JWT ---
    JWT_SECRET: str           # Long random string — keep secret!
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- App ---
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Pydantic v2: tell it to read from a file named '.env' in the working directory
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Create a single shared instance — import this everywhere
settings = Settings()
