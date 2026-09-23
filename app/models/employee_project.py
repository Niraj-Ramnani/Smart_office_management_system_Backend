from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.project import Project


class EmployeeProject(Base):
    __tablename__ = "employee_projects"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        primary_key=True,
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        primary_key=True,
    )

    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="employee_projects",
    )
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="employee_projects",
    )
