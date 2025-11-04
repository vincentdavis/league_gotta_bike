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
    CSRF_TRUSTED_ORIGINS: str = ""

    # Email Configuration
    DEFAULT_FROM_EMAIL: str = "noreply@signup.gotta.bike"
    RESEND_API_KEY: str = ""

    # Media and Static
    MEDIA_ROOT: str = "media"
    STATIC_ROOT: str = "staticfiles"

    # Logging
    LOGFIRE_TOKEN: str = ""

    # Testing
    TEST_TO_EMAIL: str = ""
    TEST_TO_PHONE_NUMBER: str = ""  # Phone number for SMS testing (E.164 format, e.g., +15555555555)

    # Sinch SMS Verification
    SINCH_SMS_AUTH_TOKEN: str = ""
    SINCH_PLAN_ID: str = ""
    SINCH_URL: str = "https://sms.api.sinch.com/xms/v1/"
    SINCH_FROM_NUMBER: str = ""  # Your Sinch phone number

    # Superuser Credentials (for automatic superuser creation)
    DJANGO_SUPERUSER_USERNAME: str = ""
    DJANGO_SUPERUSER_EMAIL: str = ""
    DJANGO_SUPERUSER_PASSWORD: str = ""

    # Admin API
    ADMIN_API_KEY: str = ""  # API key for triggering admin tasks via /api/admin/ endpoints

    # Cloudflare R2 Object Storage (S3-compatible)
    USE_S3: bool = False
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_STORAGE_BUCKET_NAME: str = ""
    AWS_S3_ENDPOINT_URL: str = ""
    AWS_S3_REGION_NAME: str = "auto"
    AWS_S3_CUSTOM_DOMAIN: str = ""

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

    @field_validator("CSRF_TRUSTED_ORIGINS", mode="after")
    @classmethod
    def parse_csrf_trusted_origins(cls, v: str) -> list[str]:
        """Parse comma-separated CSRF_TRUSTED_ORIGINS into list"""
        if not v:
            return []
        return [origin.strip() for origin in v.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
