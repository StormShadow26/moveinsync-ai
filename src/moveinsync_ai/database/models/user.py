"""User persistence model and access type."""

from datetime import datetime
from enum import Enum as PythonEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .company import Company


class UserType(str, PythonEnum):
    """Supported access models for platform users."""

    INTERNAL_OPS_MANAGER = "internal_ops_manager"
    CLIENT_TRANSPORT_ADMIN = "client_transport_admin"


class User(Base):
    """Authenticated user with either platform-wide or single-company access."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType, name="user_type", values_callable=lambda enum_class: [member.value for member in enum_class])
    )
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    company: Mapped[Company | None] = relationship(back_populates="users")

    __table_args__ = (
        CheckConstraint(
            "(user_type = 'internal_ops_manager' AND company_id IS NULL) OR "
            "(user_type = 'client_transport_admin' AND company_id IS NOT NULL)",
            name="valid_user_type_company_scope",
        ),
    )
