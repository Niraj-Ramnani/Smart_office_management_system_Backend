import csv
import io
import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER
from app.models.user import User
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user_management import (
    CSVUserRowError,
    RoleResponse,
    UserManagementResponse,
    UserProvisionCSVResponse,
    UserProvisionRequest,
)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class UserService:
    @staticmethod
    def _to_response(user: User) -> UserManagementResponse:
        emp_name = None
        emp_code = None
        if user.employee:
            emp_name = f"{user.employee.first_name} {user.employee.last_name}"
            emp_code = user.employee.employee_code

        return UserManagementResponse(
            id=user.id,
            email=user.email,
            sso_user_id=user.sso_user_id,
            role_id=user.role_id,
            role_name=user.role.name if user.role else "Unknown",
            employee_id=user.employee_id,
            employee_name=emp_name,
            employee_code=emp_code,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def list_roles(db: Session) -> list[RoleResponse]:
        roles = UserRepository.get_roles(db)
        return [RoleResponse.model_validate(r) for r in roles]

    @staticmethod
    def list_users(db: Session) -> list[UserManagementResponse]:
        users = UserRepository.get_all(db)
        return [UserService._to_response(u) for u in users]

    @staticmethod
    def assign_user_employee(
        db: Session, user_id: int, employee_id: int | None
    ) -> UserManagementResponse:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        if employee_id is not None:
            employee = EmployeeRepository.get_by_id(db, employee_id)
            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee with ID {employee_id} not found",
                )

            conflict = UserRepository.get_by_employee_id(
                db, employee_id, exclude_user_id=user_id
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee '{employee.first_name} {employee.last_name}' is already linked to user '{conflict.email}'",
                )

            user = UserRepository.update_employee_link(db, user, employee_id)
        else:
            user = UserRepository.update_employee_link(db, user, None)

        return UserService._to_response(user)

    @staticmethod
    def update_user_role(
        db: Session, user_id: int, role_name: str
    ) -> UserManagementResponse:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        role = UserRepository.get_role_by_name(db, role_name)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_name}' does not exist. Valid roles are: {ROLE_ADMIN}, {ROLE_MANAGER}, {ROLE_EMPLOYEE}",
            )

        user = UserRepository.update_role(db, user, role.id)
        return UserService._to_response(user)

    @staticmethod
    def update_user_status(
        db: Session, user_id: int, is_active: bool
    ) -> UserManagementResponse:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        user = UserRepository.update_status(db, user, is_active)
        return UserService._to_response(user)

    @staticmethod
    def provision_user(
        db: Session, data: UserProvisionRequest
    ) -> UserManagementResponse:
        employee = EmployeeRepository.get_by_id(db, data.employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with ID {data.employee_id} not found",
            )

        existing_link = UserRepository.get_by_employee_id(db, data.employee_id)
        if existing_link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee '{employee.first_name} {employee.last_name}' is already linked to user '{existing_link.email}'",
            )

        oid = data.sso_user_id.strip() if data.sso_user_id else ""
        if not oid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Microsoft Entra OID is required",
            )

        conflict_oid = UserRepository.get_by_sso_id(db, oid)
        if conflict_oid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Microsoft Entra OID '{oid}' is already registered to user '{conflict_oid.email}'",
            )

        raw_email = (data.email.strip() if data.email else "") or employee.email
        email = raw_email.strip().lower()
        if not email or not EMAIL_REGEX.match(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email address '{raw_email}'",
            )

        conflict_email = UserRepository.get_by_email(db, email)
        if conflict_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{email}' already exists",
            )

        role = UserRepository.get_role_by_name(db, data.role_name)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{data.role_name}' does not exist. Valid roles are: {ROLE_ADMIN}, {ROLE_MANAGER}, {ROLE_EMPLOYEE}",
            )

        user = UserRepository.create(
            db=db,
            email=email,
            sso_user_id=oid,
            role_id=role.id,
            employee_id=employee.id,
            is_active=True,
        )
        return UserService._to_response(user)

    @staticmethod
    def provision_users_csv(
        db: Session, csv_content: str
    ) -> UserProvisionCSVResponse:
        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file is empty",
            )

        field_map = {col.strip().lower(): col for col in reader.fieldnames if col}
        required_cols = {"employee_id", "email", "entra_oid", "role"}
        missing_headers = required_cols - set(field_map.keys())
        if missing_headers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required CSV columns: {', '.join(sorted(missing_headers))}",
            )

        existing_emails = UserRepository.get_all_emails_set(db)
        existing_oids = UserRepository.get_all_sso_ids_set(db)
        existing_linked_emp_ids = UserRepository.get_all_linked_employee_ids_set(db)
        emp_map = {e.id: e for e in EmployeeRepository.get_all(db)}
        roles_map = {r.name.lower(): r for r in UserRepository.get_roles(db)}

        batch_emails: set[str] = set()
        batch_oids: set[str] = set()
        batch_emp_ids: set[int] = set()
        errors: list[CSVUserRowError] = []
        rows_to_insert: list[dict] = []

        total_rows = 0
        for row_idx, row in enumerate(reader, start=2):
            total_rows += 1
            raw_emp_id = (row.get(field_map["employee_id"]) or "").strip()
            email = (row.get(field_map["email"]) or "").strip().lower()
            oid = (row.get(field_map["entra_oid"]) or "").strip()
            role_str = (row.get(field_map["role"]) or "").strip().lower()

            emp_id: int | None = None
            if not raw_emp_id:
                errors.append(CSVUserRowError(row=row_idx, field="employee_id", message="Employee ID is required"))
            else:
                try:
                    emp_id = int(raw_emp_id)
                except ValueError:
                    errors.append(CSVUserRowError(row=row_idx, field="employee_id", message=f"Employee ID '{raw_emp_id}' must be an integer"))

            if emp_id is not None:
                if emp_id not in emp_map:
                    errors.append(CSVUserRowError(row=row_idx, field="employee_id", message=f"Employee with ID {emp_id} does not exist"))
                elif emp_id in existing_linked_emp_ids or emp_id in batch_emp_ids:
                    errors.append(CSVUserRowError(row=row_idx, field="employee_id", message=f"Employee ID {emp_id} is already linked to a user account"))
                else:
                    batch_emp_ids.add(emp_id)

            if not email:
                errors.append(CSVUserRowError(row=row_idx, field="email", message="Email is required"))
            elif not EMAIL_REGEX.match(email):
                errors.append(CSVUserRowError(row=row_idx, field="email", message=f"Invalid email format '{email}'"))
            elif email in existing_emails or email in batch_emails:
                errors.append(CSVUserRowError(row=row_idx, field="email", message=f"User with email '{email}' already exists"))
            else:
                batch_emails.add(email)

            if not oid:
                errors.append(CSVUserRowError(row=row_idx, field="entra_oid", message="Microsoft Entra OID is required"))
            elif oid.lower() in existing_oids or oid.lower() in batch_oids:
                errors.append(CSVUserRowError(row=row_idx, field="entra_oid", message=f"Microsoft Entra OID '{oid}' is already registered"))
            else:
                batch_oids.add(oid.lower())

            role_obj = roles_map.get(role_str)
            if not role_str:
                errors.append(CSVUserRowError(row=row_idx, field="role", message="Role is required"))
            elif not role_obj:
                errors.append(CSVUserRowError(row=row_idx, field="role", message=f"Role '{role_str}' is invalid. Valid roles: {ROLE_ADMIN}, {ROLE_MANAGER}, {ROLE_EMPLOYEE}"))

            if emp_id is not None and emp_id in emp_map and role_obj:
                rows_to_insert.append({
                    "email": email,
                    "sso_user_id": oid,
                    "role_id": role_obj.id,
                    "employee_id": emp_id,
                    "is_active": True,
                })

        if errors:
            return UserProvisionCSVResponse(
                total_rows=total_rows,
                imported_count=0,
                failed_count=len(errors),
                errors=errors,
            )

        UserRepository.bulk_create(db, rows_to_insert)

        return UserProvisionCSVResponse(
            total_rows=total_rows,
            imported_count=len(rows_to_insert),
            failed_count=0,
            errors=[],
        )
