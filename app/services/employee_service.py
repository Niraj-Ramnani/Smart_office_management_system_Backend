import csv
import io
import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import EMPLOYEE_STATUS_ACTIVE, EMPLOYEE_STATUS_INACTIVE, ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.employee import (
    CSVImportSummaryResponse,
    CSVRowError,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employee_onboarding_service import EmployeeOnboardingService

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class EmployeeService:
    @staticmethod
    def _build_response(employee: Employee) -> EmployeeResponse:
        res = EmployeeResponse.model_validate(employee)
        if employee.manager:
            res.manager_name = f"{employee.manager.first_name} {employee.manager.last_name}"
        if employee.team:
            res.team_name = employee.team.name
        if employee.user:
            res.is_user_linked = True
            res.user_id = employee.user.id
            if employee.user.role:
                res.role_name = employee.user.role.name
        else:
            res.is_user_linked = False
        return res

    @staticmethod
    def list_employees(
        db: Session,
        search: str | None = None,
        department: str | None = None,
        team_id: int | None = None,
        employee_status: str | None = None,
    ) -> list[EmployeeResponse]:
        employees = EmployeeRepository.get_all(
            db,
            search=search,
            department=department,
            team_id=team_id,
            employee_status=employee_status,
        )
        return [EmployeeService._build_response(e) for e in employees]

    @staticmethod
    def get_employee(db: Session, employee_id: int) -> Employee:
        employee = EmployeeRepository.get_by_id(db, employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found",
            )
        return employee

    @staticmethod
    def get_employee_response(db: Session, employee_id: int) -> EmployeeResponse:
        employee = EmployeeService.get_employee(db, employee_id)
        return EmployeeService._build_response(employee)

    @staticmethod
    def create_employee(db: Session, data: EmployeeCreate) -> EmployeeResponse:
        return EmployeeOnboardingService.onboard_employee(db, data)

    @staticmethod
    def update_employee(
        db: Session, employee_id: int, data: EmployeeUpdate
    ) -> EmployeeResponse:
        employee = EmployeeService.get_employee(db, employee_id)
        fields_to_update: dict[str, Any] = {}

        if data.employee_code is not None:
            code_clean = data.employee_code.strip()
            conflict = EmployeeRepository.get_by_code(
                db, code_clean, exclude_id=employee_id
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee code '{code_clean}' already in use",
                )
            fields_to_update["employee_code"] = code_clean

        if data.email is not None:
            email_clean = data.email.strip().lower()
            conflict = EmployeeRepository.get_by_email(
                db, email_clean, exclude_id=employee_id
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee email '{email_clean}' already in use",
                )
            fields_to_update["email"] = email_clean

        if data.manager_id is not None:
            if data.manager_id == employee_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee cannot be their own manager",
                )
            manager = EmployeeRepository.get_by_id(db, data.manager_id)
            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Referenced manager does not exist",
                )
            fields_to_update["manager_id"] = data.manager_id
        elif data.manager_id is None and "manager_id" in data.model_fields_set:
            fields_to_update["manager_id"] = None

        if data.team_id is not None:
            team = TeamRepository.get_by_id(db, data.team_id)
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Referenced team does not exist",
                )
            fields_to_update["team_id"] = data.team_id
        elif data.team_id is None and "team_id" in data.model_fields_set:
            fields_to_update["team_id"] = None

        if data.first_name is not None:
            fields_to_update["first_name"] = data.first_name.strip()
        if data.last_name is not None:
            fields_to_update["last_name"] = data.last_name.strip()
        if data.phone is not None:
            fields_to_update["phone"] = data.phone.strip() if data.phone else None
        if data.designation is not None:
            fields_to_update["designation"] = data.designation.strip()
        if data.department is not None:
            fields_to_update["department"] = data.department.strip()
        if data.employment_type is not None:
            fields_to_update["employment_type"] = data.employment_type.strip()
        if data.employee_status is not None:
            fields_to_update["employee_status"] = data.employee_status.strip()

        updated = EmployeeRepository.update(db, employee, **fields_to_update)

        if data.role_name is not None:
            role_obj = UserRepository.get_role_by_name(db, data.role_name.strip())
            if not role_obj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role '{data.role_name}' does not exist",
                )
            if updated.user:
                UserRepository.update_role(db, updated.user, role_obj.id)
            else:
                UserRepository.create(
                    db=db,
                    email=updated.email,
                    sso_user_id=None,
                    role_id=role_obj.id,
                    employee_id=updated.id,
                    is_active=True,
                )
            db.refresh(updated)

        return EmployeeService._build_response(updated)

    @staticmethod
    def update_employee_status(
        db: Session, employee_id: int, new_status: str
    ) -> EmployeeResponse:
        employee = EmployeeService.get_employee(db, employee_id)
        updated = EmployeeRepository.update_status(db, employee, new_status)
        return EmployeeService._build_response(updated)

    @staticmethod
    def delete_employee(db: Session, employee_id: int) -> EmployeeResponse:
        return EmployeeService.update_employee_status(
            db, employee_id, EMPLOYEE_STATUS_INACTIVE
        )

    @staticmethod
    def import_employees_csv(
        db: Session, csv_content: str
    ) -> CSVImportSummaryResponse:
        return EmployeeOnboardingService.import_employees_csv(db, csv_content)

