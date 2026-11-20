"""Static implementation of the public landing page."""

from pathlib import Path

from fastapi.responses import FileResponse, Response

from .contracts import LandingPage


class StaticLandingPage:
    """Serve the versioned static landing page assets."""

    def __init__(self, static_directory: Path):
        self._static_directory = static_directory

    @property
    def static_directory(self) -> Path:
        return self._static_directory

    def response(self) -> Response:
        return FileResponse(self._static_directory / "index.html")


landing_page: LandingPage = StaticLandingPage(Path(__file__).parent / "static")
