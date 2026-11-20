"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    schema_database_url: str | None = None
    otp_secret_key: str = "development-otp-secret-change-me"
    otp_expire_minutes: int = 10
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender_email: str = "noreply@moveinsync.ai"
    groq_api_key: str | None = None
    groq_model: str = "qwen/qwen3.8-27b"
    query_row_limit: int = 100
    query_timeout_seconds: int = 10

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.getenv(
            "DATABASE_URL", "postgresql+psycopg://moveinsync:moveinsync@localhost:5432/moveinsync"
        )
        return cls(
            database_url=database_url,
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "development-only-change-me"),
            jwt_algorithm="HS256",
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            schema_database_url=os.getenv("SCHEMA_DATABASE_URL", database_url),
            otp_secret_key=os.getenv("OTP_SECRET_KEY", "development-otp-secret-change-me"),
            otp_expire_minutes=int(os.getenv("OTP_EXPIRE_MINUTES", "10")),
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_sender_email=os.getenv("SMTP_SENDER_EMAIL", "noreply@moveinsync.ai"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            groq_model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
            query_row_limit=int(os.getenv("QUERY_ROW_LIMIT", "100")),
            query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "10")),
        )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings.from_environment()
