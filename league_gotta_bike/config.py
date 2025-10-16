"""Configuration management using pydantic-settings.
Loads environment variables from .env file and provides type-safe settings.
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Django Core Settings
    DEBUG: bool = False
    SECRET_KEY: str = "django-insecure-change-this-in-production"
    ALLOWED_HOSTS: str = ""
    DJANGO_PORT: int = 8002

    # Database
    DATABASE_URL: str = "sqlite:///db.sqlite3"

    # Security
    INTERNAL_IPS: str = "127.0.0.1"

    # Email Configuration
    DEFAULT_FROM_EMAIL: str = "noreply@signup.gotta.bike"
    RESEND_API_KEY: str = ""

    # Media and Static
    MEDIA_ROOT: str = "media"
    STATIC_ROOT: str = "staticfiles"

    # Logging
    LOGFIRE_TOKEN: str = ""

    @field_validator("ALLOWED_HOSTS", mode="after")
    @classmethod
    def parse_allowed_hosts(cls, v: str) -> list[str]:
        """Parse comma-separated ALLOWED_HOSTS into list"""
        if not v:
            return []
        return [host.strip() for host in v.split(",") if host.strip()]

    @field_validator("INTERNAL_IPS", mode="after")
    @classmethod
    def parse_internal_ips(cls, v: str) -> list[str]:
        """Parse comma-separated INTERNAL_IPS into list"""
        if not v:
            return ["127.0.0.1"]
        return [ip.strip() for ip in v.split(",") if ip.strip()]


# Global settings instance
settings = Settings()
