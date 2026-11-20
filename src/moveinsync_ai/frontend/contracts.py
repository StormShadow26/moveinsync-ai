"""Contracts for frontend page delivery."""

from pathlib import Path
from typing import Protocol

from fastapi.responses import Response


class LandingPage(Protocol):
    @property
    def static_directory(self) -> Path: ...

    def response(self) -> Response: ...
