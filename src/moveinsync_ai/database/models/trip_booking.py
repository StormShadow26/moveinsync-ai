"""Trip passenger booking and attendance persistence model."""

from enum import Enum as PythonEnum

from sqlalchemy import Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantScoped
from .company import Company
from .employee import Employee
from .trip import Trip


class BookingStatus(str, PythonEnum):
    BOOKED = "booked"
    BOARDED = "boarded"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class TripBooking(TenantScoped, Base):
    """One employee's booking and final attendance outcome for a trip."""

    __tablename__ = "trip_bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status", values_callable=lambda enum_class: [member.value for member in enum_class])
    )
    company: Mapped[Company] = relationship()
    trip: Mapped[Trip] = relationship()
    employee: Mapped[Employee] = relationship()

    __table_args__ = (UniqueConstraint("trip_id", "employee_id", name="one_booking_per_employee_trip"),)
