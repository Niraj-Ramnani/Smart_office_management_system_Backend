from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.constants import EMPLOYEE_STATUS_INACTIVE, ROLE_ADMIN, ROLE_MANAGER
from app.models.user import User
from app.schemas.employee import (
    CSVImportSummaryResponse,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)
from app.services.employee_service import EmployeeService


class EmployeeController:
    @staticmethod
    def list_employees(
        db: Session,
        search: str | None = None,
        department: str | None = None,
        team_id: int | None = None,
        employee_status: str | None = None,
    ) -> list[EmployeeResponse]:
        return EmployeeService.list_employees(
            db,
            search=search,
            department=department,
            team_id=team_id,
            employee_status=employee_status,
        )

    @staticmethod
    def get_employee(
        db: Session, employee_id: int, current_user: User
    ) -> EmployeeResponse:
        user_role = current_user.role.name if current_user.role else ""
        if (
            user_role not in (ROLE_ADMIN, ROLE_MANAGER)
            and current_user.employee_id != employee_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own employee record",
            )
        return EmployeeService.get_employee_response(db, employee_id)

    @staticmethod
    def create_employee(
        db: Session, data: EmployeeCreate
    ) -> EmployeeResponse:
        return EmployeeService.create_employee(db, data)

    @staticmethod
    def update_employee(
        db: Session, employee_id: int, data: EmployeeUpdate
    ) -> EmployeeResponse:
        return EmployeeService.update_employee(db, employee_id, data)

    @staticmethod
    def update_employee_status(
        db: Session, employee_id: int, data: EmployeeStatusUpdate
    ) -> EmployeeResponse:
        return EmployeeService.update_employee_status(
            db, employee_id, data.employee_status
        )

    @staticmethod
    def delete_employee(db: Session, employee_id: int) -> EmployeeResponse:
        return EmployeeService.update_employee_status(
            db, employee_id, EMPLOYEE_STATUS_INACTIVE
        )

    @staticmethod
    async def import_employees_csv(
        request: Request, db: Session
    ) -> CSVImportSummaryResponse:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            content_str = body.get("csv_content", "")
        else:
            body_bytes = await request.body()
            try:
                content_str = body_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                content_str = body_bytes.decode("latin-1", errors="replace")

        if not content_str.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV content is empty",
            )

        return EmployeeService.import_employees_csv(db, content_str)
