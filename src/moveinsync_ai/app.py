"""FastAPI application for MoveInSync AI."""

from fastapi import FastAPI

app = FastAPI(
    title="MoveInSync AI API",
    description="API for the MoveInSync AI project.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """Return a simple status message."""
    return {"message": "MoveInSync AI API is running"}


@app.get("/health")
def health_check():
    """Report whether the API is responding."""
    return {"status": "ok"}
