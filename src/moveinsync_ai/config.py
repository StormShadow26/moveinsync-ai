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

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            database_url=os.getenv(
                "DATABASE_URL", "postgresql+psycopg://moveinsync:moveinsync@localhost:5432/moveinsync"
            ),
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "development-only-change-me"),
            jwt_algorithm="HS256",
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings.from_environment()
