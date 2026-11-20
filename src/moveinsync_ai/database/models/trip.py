"""Scheduled transport trip persistence model."""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PythonEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantScoped
from .company import Company
from .route import Route
from .vehicle import Vehicle
from .vendor import Vendor


class TripStatus(str, PythonEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class Trip(TenantScoped, Base):
    """One scheduled run of a route, including its operational outcome."""

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    trip_number: Mapped[str] = mapped_column(String(48), unique=True)
    scheduled_pickup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    scheduled_drop_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_drop_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[TripStatus] = mapped_column(
        Enum(TripStatus, name="trip_status", values_callable=lambda enum_class: [member.value for member in enum_class])
    )
    vendor_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    company: Mapped[Company] = relationship()
    route: Mapped[Route] = relationship()
    vendor: Mapped[Vendor] = relationship()
    vehicle: Mapped[Vehicle] = relationship()
