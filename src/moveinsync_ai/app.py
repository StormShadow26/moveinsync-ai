"""FastAPI application for MoveInSync AI."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from .api.routers.auth import router as auth_router
from .config import Settings, get_settings
from .database.session import create_schema


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Create an application instance, allowing isolated settings in tests."""
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        create_schema(resolved_settings)
        yield

    application = FastAPI(
        title="MoveInSync AI API",
        description="Read-only transport data assistant.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.include_router(auth_router)

    @application.get("/")
    def read_root():
        """Return a simple status message."""
        return {"message": "MoveInSync AI API is running"}

    @application.get("/health")
    def health_check():
        """Report whether the API is responding."""
        return {"status": "ok"}

    return application


app = create_app()
