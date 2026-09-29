import csv
import io
import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import (
    ASSET_STATUS_AVAILABLE,
    ASSET_TYPE_DESKTOP,
    EMPLOYEE_STATUS_ACTIVE,
    EMPLOYEE_STATUS_INACTIVE,
    EMPLOYMENT_TYPES,
    ROLE_ADMIN,
    ROLE_EMPLOYEE,
    ROLE_MANAGER,
)
from app.models.asset import Asset
from app.models.asset_allocation import AssetAllocation
from app.models.employee import Employee
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.employee import (
    CSVImportSummaryResponse,
    CSVRowError,
    CSVValidationResponse,
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

            EmployeeOnboardingService._provision_onboarding_desktop(db, target_employee.id)

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
    def _parse_and_validate_csv(
        db: Session, csv_content: str
    ) -> tuple[int, list[dict[str, Any]], int, int, list[CSVRowError]]:
        """
        Parses and validates CSV content for employee bulk onboarding.
        Returns:
            (total_rows, parsed_rows, to_create_count, to_update_count, errors)
        """
        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)

        required_cols = {
            "employee_code",
            "first_name",
            "last_name",
            "email",
            "entra_oid",
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

        existing_employees = EmployeeRepository.get_all(db)
        emp_by_code: dict[str, Employee] = {
            e.employee_code.lower(): e for e in existing_employees if e.employee_code
        }
        emp_by_email: dict[str, Employee] = {
            e.email.lower(): e for e in existing_employees if e.email
        }
        existing_users = db.query(User).all()
        user_by_email: dict[str, User] = {
            u.email.lower(): u for u in existing_users if u.email
        }
        user_by_sso: dict[str, User] = {
            u.sso_user_id.lower(): u for u in existing_users if u.sso_user_id
        }
        teams_by_name = {t.name.lower(): t.id for t in TeamRepository.get_all(db)}
        roles_by_name = {r.name.lower(): r for r in UserRepository.get_roles(db)}
        valid_emp_types = {t.lower(): t for t in EMPLOYMENT_TYPES}
        valid_statuses = {
            EMPLOYEE_STATUS_ACTIVE.lower(): EMPLOYEE_STATUS_ACTIVE,
            EMPLOYEE_STATUS_INACTIVE.lower(): EMPLOYEE_STATUS_INACTIVE,
        }

        batch_codes: dict[str, int] = {}
        batch_emails: dict[str, int] = {}
        batch_sso_ids: dict[str, int] = {}
        errors: list[CSVRowError] = []
        parsed_rows: list[dict[str, Any]] = []

        total_rows = 0
        for row_idx, row in enumerate(reader, start=2):
            total_rows += 1
            code = (row.get(field_map.get("employee_code", "")) or "").strip()
            first_name = (row.get(field_map.get("first_name", "")) or "").strip()
            last_name = (row.get(field_map.get("last_name", "")) or "").strip()
            email = (row.get(field_map.get("email", "")) or "").strip().lower()
            sso_id = (
                (row.get(field_map.get("entra_oid", "")) or "")
                or (row.get(field_map.get("sso_user_id", "")) or "")
            ).strip()
            designation = (row.get(field_map.get("designation", "")) or "").strip()
            department = (row.get(field_map.get("department", "")) or "").strip()
            employment_type_raw = (row.get(field_map.get("employment_type", "")) or "").strip()
            phone = (row.get(field_map.get("phone", "")) or "").strip() or None
            status_val_raw = (row.get(field_map.get("employee_status", "")) or "").strip()
            role_val_raw = (
                (row.get(field_map.get("role", "")) or "")
                or (row.get(field_map.get("role_name", "")) or "")
            ).strip()
            manager_ident = (
                (row.get(field_map.get("manager_employee_code", "")) or "")
                or (row.get(field_map.get("manager_code", "")) or "")
                or (row.get(field_map.get("manager_email", "")) or "")
            ).strip()
            team_name_raw = (
                (row.get(field_map.get("team_name", "")) or "")
                or (row.get(field_map.get("team", "")) or "")
            ).strip()

            emp_display = f"{first_name} {last_name}".strip()
            if code:
                emp_display = f"{emp_display} ({code})" if emp_display else code
            elif not emp_display:
                emp_display = f"Row {row_idx}"

            if not code:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="employee_code", message="Employee code is required"))
            elif code.lower() in batch_codes:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="employee_code", message=f"Duplicate employee code '{code}' in CSV (previously on row {batch_codes[code.lower()]})"))
            else:
                batch_codes[code.lower()] = row_idx

            if not first_name:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="first_name", message="First name is required"))
            if not last_name:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="last_name", message="Last name is required"))

            if not email:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="email", message="Email is required"))
            elif not EMAIL_REGEX.match(email):
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="email", message=f"Invalid email format '{email}'"))
            elif email in batch_emails:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="email", message=f"Duplicate email '{email}' in CSV (previously on row {batch_emails[email]})"))
            else:
                batch_emails[email] = row_idx

            if not sso_id:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="entra_oid", message="Microsoft Entra Object ID (entra_oid) is required"))
            elif sso_id.lower() in batch_sso_ids:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="entra_oid", message=f"Duplicate Microsoft Entra OID '{sso_id}' in CSV (previously on row {batch_sso_ids[sso_id.lower()]})"))
            elif " " in sso_id or len(sso_id) < 8:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="entra_oid", message=f"Invalid Microsoft Entra OID format '{sso_id}'"))
            else:
                batch_sso_ids[sso_id.lower()] = row_idx

            if not designation:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="designation", message="Designation is required"))
            if not department:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="department", message="Department is required"))

            employment_type = ""
            if not employment_type_raw:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="employment_type", message="Employment type is required"))
            elif employment_type_raw.lower() not in valid_emp_types:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="employment_type", message=f"Invalid employment type '{employment_type_raw}'. Valid options: {', '.join(EMPLOYMENT_TYPES)}"))
            else:
                employment_type = valid_emp_types[employment_type_raw.lower()]

            if not status_val_raw:
                employee_status = EMPLOYEE_STATUS_ACTIVE
            elif status_val_raw.lower() not in valid_statuses:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="employee_status", message=f"Invalid employee status '{status_val_raw}'. Valid options: ACTIVE, INACTIVE"))
                employee_status = EMPLOYEE_STATUS_ACTIVE
            else:
                employee_status = valid_statuses[status_val_raw.lower()]

            role_val = role_val_raw.lower() or ROLE_EMPLOYEE.lower()
            role_obj = roles_by_name.get(role_val)
            if not role_obj:
                errors.append(CSVRowError(row=row_idx, employee=emp_display, field="role", message=f"Role '{role_val_raw}' is invalid. Valid roles: {ROLE_ADMIN}, {ROLE_MANAGER}, {ROLE_EMPLOYEE}"))

            team_id = None
            if team_name_raw:
                if team_name_raw.lower() in teams_by_name:
                    team_id = teams_by_name[team_name_raw.lower()]
                else:
                    errors.append(CSVRowError(row=row_idx, employee=emp_display, field="team_name", message=f"Team '{team_name_raw}' not found"))

            existing_emp = None
            if code and code.lower() in emp_by_code:
                existing_emp = emp_by_code[code.lower()]
                if email and existing_emp.email.lower() != email:
                    if email in emp_by_email and emp_by_email[email].id != existing_emp.id:
                        errors.append(CSVRowError(row=row_idx, employee=emp_display, field="employee_code", message=f"Employee code '{code}' and email '{email}' belong to different existing employees"))
                    else:
                        errors.append(CSVRowError(row=row_idx, employee=emp_display, field="email", message=f"Employee code '{code}' is already associated with email '{existing_emp.email}' in database"))
            elif email and email in emp_by_email:
                existing_emp = emp_by_email[email]
                if code and existing_emp.employee_code.lower() != code.lower():
                    errors.append(CSVRowError(row=row_idx, employee=emp_display, field="employee_code", message=f"Email '{email}' is already associated with employee code '{existing_emp.employee_code}' in database"))

            if email and email in user_by_email:
                usr = user_by_email[email]
                if usr.employee_id and (not existing_emp or usr.employee_id != existing_emp.id):
                    errors.append(CSVRowError(row=row_idx, employee=emp_display, field="email", message=f"User email '{email}' is already linked to another employee record"))

            if sso_id and sso_id.lower() in user_by_sso:
                usr_sso = user_by_sso[sso_id.lower()]
                if usr_sso.employee_id and (not existing_emp or usr_sso.employee_id != existing_emp.id):
                    errors.append(CSVRowError(row=row_idx, employee=emp_display, field="entra_oid", message=f"Microsoft Entra OID '{sso_id}' is already linked to another employee ({usr_sso.email})"))
                elif usr_sso.email.lower() != email:
                    errors.append(CSVRowError(row=row_idx, employee=emp_display, field="entra_oid", message=f"Microsoft Entra OID '{sso_id}' is already registered to user '{usr_sso.email}'"))

            parsed_rows.append({
                "row_idx": row_idx,
                "emp_display": emp_display,
                "code": code,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "sso_id": sso_id,
                "phone": phone,
                "designation": designation,
                "department": department,
                "employment_type": employment_type,
                "employee_status": employee_status,
                "manager_ident": manager_ident,
                "team_id": team_id,
                "role_obj": role_obj,
                "is_update": existing_emp is not None,
            })

        for r in parsed_rows:
            mgr_ident = r["manager_ident"]
            if mgr_ident:
                mgr_lower = mgr_ident.lower()
                if mgr_lower in emp_by_code or mgr_lower in emp_by_email or mgr_lower in batch_codes:
                    pass
                else:
                    errors.append(CSVRowError(
                        row=r["row_idx"],
                        employee=r["emp_display"],
                        field="manager_employee_code",
                        message=f"Manager '{mgr_ident}' not found in organization or current CSV batch",
                    ))

        to_create_count = sum(1 for r in parsed_rows if not r["is_update"])
        to_update_count = sum(1 for r in parsed_rows if r["is_update"])

        return total_rows, parsed_rows, to_create_count, to_update_count, errors

    @staticmethod
    def validate_employees_csv(
        db: Session, csv_content: str
    ) -> CSVValidationResponse:
        total_rows, parsed_rows, to_create, to_update, errors = (
            EmployeeOnboardingService._parse_and_validate_csv(db, csv_content)
        )
        failed_rows = len({e.row for e in errors})
        valid_count = total_rows - failed_rows if total_rows >= failed_rows else 0

        return CSVValidationResponse(
            total_rows=total_rows,
            valid_count=valid_count,
            to_create_count=to_create if not errors else 0,
            to_update_count=to_update if not errors else 0,
            failed_count=failed_rows if errors else 0,
            errors=errors,
        )

    @staticmethod
    def import_employees_csv(
        db: Session, csv_content: str
    ) -> CSVImportSummaryResponse:
        total_rows, parsed_rows, to_create, to_update, errors = (
            EmployeeOnboardingService._parse_and_validate_csv(db, csv_content)
        )

        if errors:
            failed_rows = len({e.row for e in errors})
            return CSVImportSummaryResponse(
                total_rows=total_rows,
                imported_count=0,
                updated_count=0,
                failed_count=failed_rows,
                errors=errors,
            )

        try:
            all_emps_map: dict[str, Employee] = {
                e.employee_code.lower(): e for e in EmployeeRepository.get_all(db) if e.employee_code
            }
            emp_by_email_map: dict[str, Employee] = {
                e.email.lower(): e for e in EmployeeRepository.get_all(db) if e.email
            }
            all_users_map: dict[str, User] = {
                u.email.lower(): u for u in db.query(User).all() if u.email
            }

            created_count = 0
            updated_count = 0

            for r in parsed_rows:
                code_lower = r["code"].lower()
                email_lower = r["email"].lower()
                emp = all_emps_map.get(code_lower) or emp_by_email_map.get(email_lower)

                if emp:
                    emp.employee_code = r["code"]
                    emp.first_name = r["first_name"]
                    emp.last_name = r["last_name"]
                    emp.email = r["email"]
                    emp.phone = r["phone"]
                    emp.designation = r["designation"]
                    emp.department = r["department"]
                    emp.employment_type = r["employment_type"]
                    emp.employee_status = r["employee_status"]
                    emp.team_id = r["team_id"]
                    db.flush()
                    updated_count += 1
                else:
                    emp = Employee(
                        employee_code=r["code"],
                        first_name=r["first_name"],
                        last_name=r["last_name"],
                        email=r["email"],
                        phone=r["phone"],
                        designation=r["designation"],
                        department=r["department"],
                        employment_type=r["employment_type"],
                        employee_status=r["employee_status"],
                        team_id=r["team_id"],
                    )
                    db.add(emp)
                    db.flush()
                    created_count += 1

                all_emps_map[code_lower] = emp
                emp_by_email_map[email_lower] = emp

                user = all_users_map.get(email_lower)
                is_active = (r["employee_status"] == EMPLOYEE_STATUS_ACTIVE)
                if user:
                    user.employee_id = emp.id
                    user.sso_user_id = r["sso_id"]
                    user.role_id = r["role_obj"].id
                    user.is_active = is_active
                else:
                    user = User(
                        email=r["email"],
                        sso_user_id=r["sso_id"],
                        role_id=r["role_obj"].id,
                        employee_id=emp.id,
                        is_active=is_active,
                    )
                    db.add(user)
                    db.flush()
                    all_users_map[email_lower] = user

                EmployeeOnboardingService._provision_onboarding_desktop(db, emp.id)

            for r in parsed_rows:
                mgr_ident = r["manager_ident"]
                if mgr_ident:
                    mgr_lower = mgr_ident.lower()
                    mgr = all_emps_map.get(mgr_lower) or emp_by_email_map.get(mgr_lower)
                    if mgr:
                        emp = all_emps_map.get(r["code"].lower())
                        if emp:
                            emp.manager_id = mgr.id

            db.commit()
            return CSVImportSummaryResponse(
                total_rows=total_rows,
                imported_count=created_count,
                updated_count=updated_count,
                failed_count=0,
                errors=[],
            )
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _provision_onboarding_desktop(db: Session, employee_id: int):
        active_desktop = (
            db.query(AssetAllocation)
            .join(Asset)
            .filter(
                AssetAllocation.employee_id == employee_id,
                AssetAllocation.status == "ACTIVE",
                Asset.asset_type == ASSET_TYPE_DESKTOP,
            )
            .first()
        )
        if active_desktop:
            return

        avail_desktop = (
            db.query(Asset)
            .filter(Asset.asset_type == ASSET_TYPE_DESKTOP, Asset.status == ASSET_STATUS_AVAILABLE)
            .first()
        )
        if not avail_desktop:
            count = db.query(Asset).filter(Asset.asset_type == ASSET_TYPE_DESKTOP).count() + 1
            avail_desktop = Asset(
                asset_code=f"DSK-{count:03d}",
                asset_type=ASSET_TYPE_DESKTOP,
                name=f"Corporate Desktop Tower (#{count:03d})",
                serial_number=f"SN-DSK-{count:04d}-{employee_id}",
                status=ASSET_STATUS_AVAILABLE,
            )
            db.add(avail_desktop)
            db.flush()

        AssetRepository.allocate_asset(
            db=db,
            asset=avail_desktop,
            employee_id=employee_id,
            notes="Standard onboarding desktop provision",
        )
