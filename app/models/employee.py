from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.asset_allocation import AssetAllocation
    from app.models.employee_project import EmployeeProject
    from app.models.guest_seat_allocation import GuestSeatAllocation
    from app.models.hot_desk_booking import HotDeskBooking
    from app.models.permission_request import PermissionRequest
    from app.models.seat import Seat
    from app.models.seat_history import SeatHistory


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    employee_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ACTIVE",
    )
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
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

    user = relationship("User", back_populates="employee", uselist=False)
    manager = relationship(
        "Employee",
        remote_side="Employee.id",
        back_populates="team_members",
    )
    team_members = relationship(
        "Employee",
        back_populates="manager",
    )
    team = relationship(
        "Team",
        back_populates="employees",
        foreign_keys=[team_id],
    )
    employee_projects: Mapped[list["EmployeeProject"]] = relationship(
        "EmployeeProject",
        back_populates="employee",
    )
    seat: Mapped["Seat | None"] = relationship(
        "Seat",
        back_populates="employee",
        uselist=False,
    )
    seat_histories: Mapped[list["SeatHistory"]] = relationship(
        "SeatHistory",
        back_populates="employee",
    )
    asset_allocations: Mapped[list["AssetAllocation"]] = relationship(
        "AssetAllocation",
        back_populates="employee",
    )
    permission_requests: Mapped[list["PermissionRequest"]] = relationship(
        "PermissionRequest",
        foreign_keys="PermissionRequest.employee_id",
        back_populates="employee",
    )
    approved_permission_requests: Mapped[list["PermissionRequest"]] = relationship(
        "PermissionRequest",
        foreign_keys="PermissionRequest.approved_by",
        back_populates="approver",
    )
    assigned_permission_requests: Mapped[list["PermissionRequest"]] = relationship(
        "PermissionRequest",
        foreign_keys="PermissionRequest.assigned_to",
        back_populates="assignee",
    )
    hot_desk_bookings: Mapped[list["HotDeskBooking"]] = relationship(
        "HotDeskBooking",
        back_populates="employee",
    )
    guest_seat_allocations: Mapped[list["GuestSeatAllocation"]] = relationship(
        "GuestSeatAllocation",
        back_populates="employee",
    )