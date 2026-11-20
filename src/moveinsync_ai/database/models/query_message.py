"""Persisted messages belonging to a scoped data-query thread."""

from datetime import datetime
from enum import Enum as PythonEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .company import Company
from .query_thread import QueryThread
from .user import User


class QueryMessageRole(str, PythonEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class QueryMessage(Base):
    """A chat message and optional inspected SQL/result summary."""

    __tablename__ = "query_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("query_threads.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    role: Mapped[QueryMessageRole] = mapped_column(
        Enum(QueryMessageRole, name="query_message_role", values_callable=lambda enum_class: [member.value for member in enum_class])
    )
    content: Mapped[str] = mapped_column(Text)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    thread: Mapped[QueryThread] = relationship()
    user: Mapped[User] = relationship()
    company: Mapped[Company | None] = relationship()
