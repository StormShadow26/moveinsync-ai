"""Passenger/employee persistence model."""

from sqlalchemy import Boolean, Integer, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantScoped
from .company import Company


class Employee(TenantScoped, Base):
    """An employee eligible to book transport for one company."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str] = mapped_column(String(255))
    office_location: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    company: Mapped[Company] = relationship()

    __table_args__ = (UniqueConstraint("company_id", "employee_code", name="unique_employee_code_per_company"),)
