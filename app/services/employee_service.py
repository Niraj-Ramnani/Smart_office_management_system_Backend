import csv
import io
import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import EMPLOYEE_STATUS_ACTIVE, EMPLOYEE_STATUS_INACTIVE
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.team_repository import TeamRepository
from app.schemas.employee import (
    CSVImportSummaryResponse,
    CSVRowError,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class EmployeeService:
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
        result = []
        for e in employees:
            res = EmployeeResponse.model_validate(e)
            if e.manager:
                res.manager_name = f"{e.manager.first_name} {e.manager.last_name}"
            if e.team:
                res.team_name = e.team.name
            res.is_user_linked = e.user is not None
            result.append(res)
        return result

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
        res = EmployeeResponse.model_validate(employee)
        if employee.manager:
            res.manager_name = f"{employee.manager.first_name} {employee.manager.last_name}"
        if employee.team:
            res.team_name = employee.team.name
        res.is_user_linked = employee.user is not None
        return res

    @staticmethod
    def create_employee(db: Session, data: EmployeeCreate) -> EmployeeResponse:
        code_clean = data.employee_code.strip()
        email_clean = data.email.strip().lower()

        existing_code = EmployeeRepository.get_by_code(db, code_clean)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee code '{code_clean}' already exists",
            )

        existing_email = EmployeeRepository.get_by_email(db, email_clean)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee email '{email_clean}' already exists",
            )

        if data.manager_id is not None:
            manager = EmployeeRepository.get_by_id(db, data.manager_id)
            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Referenced manager does not exist",
                )

        if data.team_id is not None:
            team = TeamRepository.get_by_id(db, data.team_id)
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Referenced team does not exist",
                )

        employee = EmployeeRepository.create(
            db,
            employee_code=code_clean,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            email=email_clean,
            phone=data.phone.strip() if data.phone else None,
            designation=data.designation.strip(),
            department=data.department.strip(),
            employment_type=data.employment_type.strip(),
            employee_status=data.employee_status.strip() or EMPLOYEE_STATUS_ACTIVE,
            manager_id=data.manager_id,
            team_id=data.team_id,
        )

        res = EmployeeResponse.model_validate(employee)
        if employee.manager:
            res.manager_name = f"{employee.manager.first_name} {employee.manager.last_name}"
        if employee.team:
            res.team_name = employee.team.name
        res.is_user_linked = False
        return res

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

        res = EmployeeResponse.model_validate(updated)
        if updated.manager:
            res.manager_name = f"{updated.manager.first_name} {updated.manager.last_name}"
        if updated.team:
            res.team_name = updated.team.name
        res.is_user_linked = updated.user is not None
        return res

    @staticmethod
    def update_employee_status(
        db: Session, employee_id: int, new_status: str
    ) -> EmployeeResponse:
        employee = EmployeeService.get_employee(db, employee_id)
        updated = EmployeeRepository.update_status(db, employee, new_status)
        res = EmployeeResponse.model_validate(updated)
        if updated.manager:
            res.manager_name = f"{updated.manager.first_name} {updated.manager.last_name}"
        if updated.team:
            res.team_name = updated.team.name
        res.is_user_linked = updated.user is not None
        return res

    @staticmethod
    def delete_employee(db: Session, employee_id: int) -> EmployeeResponse:
        return EmployeeService.update_employee_status(
            db, employee_id, EMPLOYEE_STATUS_INACTIVE
        )

    @staticmethod
    def import_employees_csv(
        db: Session, csv_content: str
    ) -> CSVImportSummaryResponse:
        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)

        required_cols = {
            "employee_code",
            "first_name",
            "last_name",
            "email",
            "designation",
            "department",
            "employment_type",
        }

        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file is empty",
            )

        headers = {col.strip().lower() for col in reader.fieldnames if col}
        missing_headers = required_cols - headers
        if missing_headers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required CSV columns: {', '.join(sorted(missing_headers))}",
            )

        field_map = {col.strip().lower(): col for col in reader.fieldnames if col}

        existing_codes = EmployeeRepository.get_all_codes_set(db)
        existing_emails = EmployeeRepository.get_all_emails_set(db)
        teams_by_name = {t.name.lower(): t.id for t in TeamRepository.get_all(db)}
        emp_by_code = EmployeeRepository.get_code_to_id_map(db)

        batch_codes: set[str] = set()
        batch_emails: set[str] = set()
        errors: list[CSVRowError] = []
        rows_to_insert: list[dict[str, Any]] = []

        total_rows = 0
        for row_idx, row in enumerate(reader, start=2):
            total_rows += 1
            code = (row.get(field_map.get("employee_code", "")) or "").strip()
            first_name = (row.get(field_map.get("first_name", "")) or "").strip()
            last_name = (row.get(field_map.get("last_name", "")) or "").strip()
            email = (row.get(field_map.get("email", "")) or "").strip().lower()
            designation = (row.get(field_map.get("designation", "")) or "").strip()
            department = (row.get(field_map.get("department", "")) or "").strip()
            employment_type = (row.get(field_map.get("employment_type", "")) or "").strip()
            phone = (row.get(field_map.get("phone", "")) or "").strip() or None
            status_val = (
                (row.get(field_map.get("employee_status", "")) or "").strip()
                or EMPLOYEE_STATUS_ACTIVE
            )
            manager_code = (
                (row.get(field_map.get("manager_employee_code", "")) or "")
                or (row.get(field_map.get("manager_code", "")) or "")
            ).strip().lower()
            team_name = (row.get(field_map.get("team_name", "")) or "").strip().lower()

            if not code:
                errors.append(CSVRowError(row=row_idx, field="employee_code", message="Employee code is required"))
            elif code.lower() in existing_codes or code.lower() in batch_codes:
                errors.append(CSVRowError(row=row_idx, field="employee_code", message=f"Duplicate employee code '{code}'"))
            else:
                batch_codes.add(code.lower())

            if not first_name:
                errors.append(CSVRowError(row=row_idx, field="first_name", message="First name is required"))
            if not last_name:
                errors.append(CSVRowError(row=row_idx, field="last_name", message="Last name is required"))

            if not email:
                errors.append(CSVRowError(row=row_idx, field="email", message="Email is required"))
            elif not EMAIL_REGEX.match(email):
                errors.append(CSVRowError(row=row_idx, field="email", message=f"Invalid email format '{email}'"))
            elif email in existing_emails or email in batch_emails:
                errors.append(CSVRowError(row=row_idx, field="email", message=f"Duplicate email '{email}'"))
            else:
                batch_emails.add(email)

            if not designation:
                errors.append(CSVRowError(row=row_idx, field="designation", message="Designation is required"))
            if not department:
                errors.append(CSVRowError(row=row_idx, field="department", message="Department is required"))
            if not employment_type:
                errors.append(CSVRowError(row=row_idx, field="employment_type", message="Employment type is required"))

            manager_id = None
            if manager_code:
                if manager_code in emp_by_code:
                    manager_id = emp_by_code[manager_code]
                else:
                    errors.append(CSVRowError(row=row_idx, field="manager_employee_code", message=f"Manager code '{manager_code}' not found"))

            team_id = None
            if team_name:
                if team_name in teams_by_name:
                    team_id = teams_by_name[team_name]
                else:
                    errors.append(CSVRowError(row=row_idx, field="team_name", message=f"Team '{team_name}' not found"))

            rows_to_insert.append({
                "employee_code": code,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "designation": designation,
                "department": department,
                "employment_type": employment_type,
                "employee_status": status_val,
                "manager_id": manager_id,
                "team_id": team_id,
            })

        if errors:
            return CSVImportSummaryResponse(
                total_rows=total_rows,
                imported_count=0,
                failed_count=len(errors),
                errors=errors,
            )

        EmployeeRepository.bulk_create(db, rows_to_insert)

        return CSVImportSummaryResponse(
            total_rows=total_rows,
            imported_count=len(rows_to_insert),
            failed_count=0,
            errors=[],
        )
