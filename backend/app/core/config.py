"""
config.py — Centralized application and security settings for Brightloop Subscription Management System.
Reads sensitive configuration from environment variables (.env), preventing hardcoded production secrets.
"""

import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    """
    PROJECT_NAME: str = "Brightloop Subscription Management System"
    ENVIRONMENT: str = "development"

    # Security & JWT Configuration
    # In development/test mode, a fallback default is provided so tests run out-of-the-box.
    # In production (ENVIRONMENT="production"), an explicit, secure SECRET_KEY is enforced.
    SECRET_KEY: str = "insecure-dev-secret-key-change-in-production-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Ensures that production deployments cannot accidentally use the default insecure key.
        """
        env = os.getenv("ENVIRONMENT", "development").strip().lower()
        if env == "production":
            if not v or "dev" in v.lower() or "insecure" in v.lower() or len(v) < 32:
                raise ValueError(
                    "Production ENVIRONMENT detected: A secure SECRET_KEY (minimum 32 characters) "
                    "must be supplied via environment variables."
                )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()

