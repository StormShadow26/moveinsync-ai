"""SQLAlchemy base classes and shared persistence concerns."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base ORM model."""


class TenantScoped:
    """Require a transport record to belong to one client company."""

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
