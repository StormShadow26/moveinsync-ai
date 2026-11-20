"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..config import Settings
from ..database.session import get_session


def app_settings(request: Request) -> Settings:
    return request.app.state.settings


def database_session(request: Request):
    yield from get_session(app_settings(request))


SettingsDependency = Annotated[Settings, Depends(app_settings)]
SessionDependency = Annotated[Session, Depends(database_session)]
