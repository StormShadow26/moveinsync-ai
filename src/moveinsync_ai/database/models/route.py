"""Transport route persistence model."""

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantScoped
from .company import Company


class Route(TenantScoped, Base):
    """A named pickup-to-destination commute route for one company."""

    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32))
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True)
    origin: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str] = mapped_column(String(255))
    distance_km: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    company: Mapped[Company] = relationship()

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="unique_route_code_per_company"),
        CheckConstraint("distance_km > 0", name="positive_route_distance"),
    )
