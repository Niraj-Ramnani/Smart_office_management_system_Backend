import csv
import io
import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import (
    EMPLOYEE_STATUS_ACTIVE,
    ROLE_ADMIN,
    ROLE_EMPLOYEE,
    ROLE_MANAGER,
)
from app.models.employee import Employee
from app.models.user import User
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.employee import (
    CSVImportSummaryResponse,
    CSVRowError,
    EmployeeCreate,
    EmployeeResponse,
)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
VALID_ROLES = {ROLE_ADMIN.lower(): ROLE_ADMIN, ROLE_MANAGER.lower(): ROLE_MANAGER, ROLE_EMPLOYEE.lower(): ROLE_EMPLOYEE}


class EmployeeOnboardingService:
    @staticmethod
    def onboard_employee(db: Session, data: EmployeeCreate) -> EmployeeResponse:
        code_clean = data.employee_code.strip()
        email_clean = data.email.strip().lower()
        sso_id_clean = data.sso_user_id.strip() if data.sso_user_id else None
        role_input = (data.role_name or ROLE_EMPLOYEE).strip()

        role_key = role_input.lower()
        if role_key not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{role_input}'. Valid roles are: {ROLE_ADMIN}, {ROLE_MANAGER}, {ROLE_EMPLOYEE}",
            )
        target_role_name = VALID_ROLES[role_key]
        role = UserRepository.get_role_by_name(db, target_role_name)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{target_role_name}' not found in database",
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

        existing_emp_by_code = EmployeeRepository.get_by_code(db, code_clean)
        existing_emp_by_email = EmployeeRepository.get_by_email(db, email_clean)
        existing_user_by_email = UserRepository.get_by_email(db, email_clean)
        existing_user_by_sso = (
            UserRepository.get_by_sso_id(db, sso_id_clean) if sso_id_clean else None
        )

        if existing_user_by_sso and existing_user_by_sso.employee_id:
            if not existing_emp_by_code or existing_user_by_sso.employee_id != existing_emp_by_code.id:
                linked_emp = existing_user_by_sso.employee
                name_display = f"{linked_emp.first_name} {linked_emp.last_name}" if linked_emp else "another employee"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Microsoft Entra identity '{sso_id_clean}' is already linked to {name_display}",
                )

        if existing_user_by_email and existing_user_by_email.employee_id:
            if not existing_emp_by_code or existing_user_by_email.employee_id != existing_emp_by_code.id:
                linked_emp = existing_user_by_email.employee
                name_display = f"{linked_emp.first_name} {linked_emp.last_name}" if linked_emp else "another employee"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entra user email '{email_clean}' is already linked to {name_display}",
                )

        if existing_emp_by_email and existing_user_by_sso:
            if existing_user_by_sso.email.lower() != email_clean:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee email '{email_clean}' already exists but belongs to a different Entra identity",
                )

        if existing_emp_by_code and existing_user_by_email and existing_user_by_email.employee_id == existing_emp_by_code.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with code '{code_clean}' and user email '{email_clean}' is already onboarded",
            )

        if existing_emp_by_code and existing_emp_by_code.email.lower() != email_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee code '{code_clean}' is already used by '{existing_emp_by_code.email}'",
            )

        try:
            target_employee: Employee
            if existing_emp_by_email:
                target_employee = existing_emp_by_email
                target_employee.employee_code = code_clean
                target_employee.first_name = data.first_name.strip()
                target_employee.last_name = data.last_name.strip()
                target_employee.phone = data.phone.strip() if data.phone else None
                target_employee.designation = data.designation.strip()
                target_employee.department = data.department.strip()
                target_employee.employment_type = data.employment_type.strip()
                target_employee.employee_status = data.employee_status.strip() or EMPLOYEE_STATUS_ACTIVE
                target_employee.manager_id = data.manager_id
                target_employee.team_id = data.team_id
            else:
                target_employee = Employee(
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
                db.add(target_employee)
                db.flush()

            target_user: User
            if existing_user_by_email:
                target_user = existing_user_by_email
                target_user.employee_id = target_employee.id
                target_user.role_id = role.id
                target_user.is_active = True
                if sso_id_clean and not target_user.sso_user_id:
                    target_user.sso_user_id = sso_id_clean
            elif existing_user_by_sso:
                target_user = existing_user_by_sso
                target_user.employee_id = target_employee.id
                target_user.email = email_clean
                target_user.role_id = role.id
                target_user.is_active = True
            else:
                target_user = User(
                    email=email_clean,
                    sso_user_id=sso_id_clean,
                    role_id=role.id,
                    employee_id=target_employee.id,
                    is_active=True,
                )
                db.add(target_user)

            db.commit()
            db.refresh(target_employee)

            res = EmployeeResponse.model_validate(target_employee)
            if target_employee.manager:
                res.manager_name = f"{target_employee.manager.first_name} {target_employee.manager.last_name}"
            if target_employee.team:
                res.team_name = target_employee.team.name
            res.is_user_linked = True
            res.role_name = target_user.role.name if target_user.role else target_role_name
            res.user_id = target_user.id
            return res
        except Exception:
            db.rollback()
            raise

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

        existing_emp_codes = EmployeeRepository.get_all_codes_set(db)
        existing_emp_emails = EmployeeRepository.get_all_emails_set(db)
        existing_user_emails = UserRepository.get_all_emails_set(db)
        existing_sso_ids = UserRepository.get_all_sso_ids_set(db)
        teams_by_name = {t.name.lower(): t.id for t in TeamRepository.get_all(db)}
        emp_by_code = EmployeeRepository.get_code_to_id_map(db)
        emp_by_email = {e.email.lower(): e.id for e in EmployeeRepository.get_all(db)}
        roles_by_name = {r.name.lower(): r for r in UserRepository.get_roles(db)}

        batch_codes: set[str] = set()
        batch_emails: set[str] = set()
        batch_sso_ids: set[str] = set()
        errors: list[CSVRowError] = []
        rows_to_process: list[dict[str, Any]] = []

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
            role_val = (
                (row.get(field_map.get("role", "")) or "")
                or (row.get(field_map.get("role_name", "")) or "")
            ).strip().lower() or ROLE_EMPLOYEE.lower()

            manager_ident = (
                (row.get(field_map.get("manager_employee_code", "")) or "")
                or (row.get(field_map.get("manager_code", "")) or "")
                or (row.get(field_map.get("manager_email", "")) or "")
            ).strip().lower()

            team_name = (
                (row.get(field_map.get("team_name", "")) or "")
                or (row.get(field_map.get("team", "")) or "")
            ).strip().lower()

            sso_id = (
                (row.get(field_map.get("entra_oid", "")) or "")
                or (row.get(field_map.get("sso_user_id", "")) or "")
            ).strip() or None

            if not code:
                errors.append(CSVRowError(row=row_idx, field="employee_code", message="Employee code is required"))
            elif code.lower() in existing_emp_codes or code.lower() in batch_codes:
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
            elif email in existing_emp_emails or email in batch_emails:
                errors.append(CSVRowError(row=row_idx, field="email", message=f"Duplicate employee email '{email}'"))
            elif email in existing_user_emails:
                errors.append(CSVRowError(row=row_idx, field="email", message=f"User email '{email}' already registered in system"))
            else:
                batch_emails.add(email)

            if sso_id:
                if sso_id.lower() in existing_sso_ids or sso_id.lower() in batch_sso_ids:
                    errors.append(CSVRowError(row=row_idx, field="entra_oid", message=f"Microsoft Entra OID '{sso_id}' already registered"))
                else:
                    batch_sso_ids.add(sso_id.lower())

            if not designation:
                errors.append(CSVRowError(row=row_idx, field="designation", message="Designation is required"))
            if not department:
                errors.append(CSVRowError(row=row_idx, field="department", message="Department is required"))
            if not employment_type:
                errors.append(CSVRowError(row=row_idx, field="employment_type", message="Employment type is required"))

            role_obj = roles_by_name.get(role_val)
            if not role_obj:
                errors.append(CSVRowError(row=row_idx, field="role", message=f"Role '{role_val}' is invalid. Valid roles: {ROLE_ADMIN}, {ROLE_MANAGER}, {ROLE_EMPLOYEE}"))

            manager_id = None
            if manager_ident:
                if manager_ident in emp_by_code:
                    manager_id = emp_by_code[manager_ident]
                elif manager_ident in emp_by_email:
                    manager_id = emp_by_email[manager_ident]
                else:
                    errors.append(CSVRowError(row=row_idx, field="manager", message=f"Manager '{manager_ident}' not found"))

            team_id = None
            if team_name:
                if team_name in teams_by_name:
                    team_id = teams_by_name[team_name]
                else:
                    errors.append(CSVRowError(row=row_idx, field="team_name", message=f"Team '{team_name}' not found"))

            if role_obj:
                rows_to_process.append({
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
                    "role_id": role_obj.id,
                    "sso_user_id": sso_id,
                })

        if errors:
            return CSVImportSummaryResponse(
                total_rows=total_rows,
                imported_count=0,
                failed_count=len(errors),
                errors=errors,
            )

        try:
            for row_data in rows_to_process:
                emp = Employee(
                    employee_code=row_data["employee_code"],
                    first_name=row_data["first_name"],
                    last_name=row_data["last_name"],
                    email=row_data["email"],
                    phone=row_data["phone"],
                    designation=row_data["designation"],
                    department=row_data["department"],
                    employment_type=row_data["employment_type"],
                    employee_status=row_data["employee_status"],
                    manager_id=row_data["manager_id"],
                    team_id=row_data["team_id"],
                )
                db.add(emp)
                db.flush()

                usr = User(
                    email=row_data["email"],
                    sso_user_id=row_data["sso_user_id"],
                    role_id=row_data["role_id"],
                    employee_id=emp.id,
                    is_active=True,
                )
                db.add(usr)

            db.commit()
            return CSVImportSummaryResponse(
                total_rows=total_rows,
                imported_count=len(rows_to_process),
                failed_count=0,
                errors=[],
            )
        except Exception:
            db.rollback()
            raise
