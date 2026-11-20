"""Conversation API request and response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..database.models import QueryMessageRole, QueryThreadScope


class CreateThreadRequest(BaseModel):
    scope: QueryThreadScope
    company_id: int | None = None
    title: str = Field(default="New conversation", min_length=1, max_length=255)


class AddMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class ThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int | None
    scope: QueryThreadScope
    title: str
    created_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    thread_id: int
    role: QueryMessageRole
    content: str
    generated_sql: str | None
    result_summary: str | None
    created_at: datetime


class AskResponse(MessageResponse):
    columns: list[str]
    rows: list[dict[str, Any]]
