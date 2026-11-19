"""MoveInSync AI application package."""

from .app import app


def main() -> None:
    """Run the API server."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
