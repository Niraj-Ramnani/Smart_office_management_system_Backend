from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.floor import Floor
    from app.models.guest_seat_allocation import GuestSeatAllocation
    from app.models.hot_desk_booking import HotDeskBooking
    from app.models.seat_history import SeatHistory


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("floor_id", "seat_number", name="uq_seats_floor_seat_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("floors.id"), nullable=False)
    seat_number: Mapped[str] = mapped_column(String(50), nullable=False)
    seat_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    x_position: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    y_position: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"),
        unique=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    floor: Mapped["Floor"] = relationship(
        "Floor",
        back_populates="seats",
    )
    employee: Mapped["Employee | None"] = relationship(
        "Employee",
        back_populates="seat",
        uselist=False,
    )
    seat_histories: Mapped[list["SeatHistory"]] = relationship(
        "SeatHistory",
        back_populates="seat",
    )
    hot_desk_bookings: Mapped[list["HotDeskBooking"]] = relationship(
        "HotDeskBooking",
        back_populates="seat",
    )
    guest_seat_allocations: Mapped[list["GuestSeatAllocation"]] = relationship(
        "GuestSeatAllocation",
        back_populates="seat",
    )
