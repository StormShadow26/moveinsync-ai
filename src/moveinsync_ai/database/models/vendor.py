"""Transport vendor persistence model."""

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantScoped
from .company import Company


class Vendor(TenantScoped, Base):
    """A transport provider contracted by one client company."""

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[Company] = relationship()

    __table_args__ = (UniqueConstraint("company_id", "code", name="unique_vendor_code_per_company"),)
