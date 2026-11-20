"""Vehicle persistence model."""

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantScoped
from .company import Company
from .vendor import Vendor


class Vehicle(TenantScoped, Base):
    """A vendor-operated vehicle available to one client company."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)
    registration_number: Mapped[str] = mapped_column(String(32), unique=True)
    model: Mapped[str] = mapped_column(String(128))
    seating_capacity: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    company: Mapped[Company] = relationship()
    vendor: Mapped[Vendor] = relationship()

    __table_args__ = (CheckConstraint("seating_capacity > 0", name="positive_vehicle_capacity"),)
