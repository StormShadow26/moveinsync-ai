"""Explicit company assignments for internal managers."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserCompany(Base):
    __tablename__ = "user_companies"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), primary_key=True)
