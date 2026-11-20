"""Persisted, explicitly scoped conversations for data questions."""

from datetime import datetime
from enum import Enum as PythonEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .company import Company
from .user import User


class QueryThreadScope(str, PythonEnum):
    COMPANY = "company"
    ALL_COMPANIES = "all_companies"


class QueryThread(Base):
    """A user's conversation with an immutable initial data scope."""

    __tablename__ = "query_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    scope: Mapped[QueryThreadScope] = mapped_column(
        Enum(QueryThreadScope, name="query_thread_scope", values_callable=lambda enum_class: [member.value for member in enum_class])
    )
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship()
    company: Mapped[Company | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "(scope = 'company' AND company_id IS NOT NULL) OR "
            "(scope = 'all_companies' AND company_id IS NULL)",
            name="valid_query_thread_scope",
        ),
    )
