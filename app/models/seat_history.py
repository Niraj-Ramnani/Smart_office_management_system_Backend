from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.seat import Seat


class SeatHistory(Base):
    __tablename__ = "seat_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )

    seat: Mapped["Seat"] = relationship(
        "Seat",
        back_populates="seat_histories",
    )
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="seat_histories",
    )
