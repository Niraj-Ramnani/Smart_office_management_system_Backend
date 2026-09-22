from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class PermissionRequest(Base):
    __tablename__ = "permission_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    request_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    requested_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    employee: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[employee_id],
        back_populates="permission_requests",
    )
    approver: Mapped["Employee | None"] = relationship(
        "Employee",
        foreign_keys=[approved_by],
        back_populates="approved_permission_requests",
    )
    assignee: Mapped["Employee | None"] = relationship(
        "Employee",
        foreign_keys=[assigned_to],
        back_populates="assigned_permission_requests",
    )
