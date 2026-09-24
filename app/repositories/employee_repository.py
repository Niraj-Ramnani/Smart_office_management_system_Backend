from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee


class EmployeeRepository:
    @staticmethod
    def get_all(
        db: Session,
        search: str | None = None,
        department: str | None = None,
        team_id: int | None = None,
        employee_status: str | None = None,
    ) -> list[Employee]:
        query = (
            db.query(Employee)
            .options(
                joinedload(Employee.manager),
                joinedload(Employee.team),
                joinedload(Employee.user),
            )
            .order_by(Employee.first_name, Employee.last_name)
        )

        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(Employee.first_name).like(s),
                    func.lower(Employee.last_name).like(s),
                    func.lower(Employee.email).like(s),
                    func.lower(Employee.employee_code).like(s),
                    func.lower(Employee.designation).like(s),
                )
            )

        if department:
            query = query.filter(
                func.lower(Employee.department) == department.strip().lower()
            )
        if team_id is not None:
            query = query.filter(Employee.team_id == team_id)
        if employee_status:
            query = query.filter(
                func.lower(Employee.employee_status) == employee_status.strip().lower()
            )

        return query.all()

    @staticmethod
    def get_by_id(db: Session, employee_id: int) -> Employee | None:
        return (
            db.query(Employee)
            .options(
                joinedload(Employee.manager),
                joinedload(Employee.team),
                joinedload(Employee.user),
            )
            .filter(Employee.id == employee_id)
            .first()
        )

    @staticmethod
    def get_by_code(
        db: Session, code: str, exclude_id: int | None = None
    ) -> Employee | None:
        query = db.query(Employee).filter(
            func.lower(Employee.employee_code) == code.strip().lower()
        )
        if exclude_id is not None:
            query = query.filter(Employee.id != exclude_id)
        return query.first()

    @staticmethod
    def get_by_email(
        db: Session, email: str, exclude_id: int | None = None
    ) -> Employee | None:
        query = db.query(Employee).filter(
            func.lower(Employee.email) == email.strip().lower()
        )
        if exclude_id is not None:
            query = query.filter(Employee.id != exclude_id)
        return query.first()

    @staticmethod
    def get_all_codes_set(db: Session) -> set[str]:
        return {
            code[0].lower() for code in db.query(Employee.employee_code).all()
        }

    @staticmethod
    def get_all_emails_set(db: Session) -> set[str]:
        return {
            email[0].lower() for email in db.query(Employee.email).all()
        }

    @staticmethod
    def get_code_to_id_map(db: Session) -> dict[str, int]:
        return {
            e.employee_code.lower(): e.id
            for e in db.query(Employee.id, Employee.employee_code).all()
        }

    @staticmethod
    def create(db: Session, **fields: Any) -> Employee:
        employee = Employee(**fields)
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def bulk_create(db: Session, rows: list[dict[str, Any]]) -> None:
        for row_data in rows:
            emp = Employee(**row_data)
            db.add(emp)
        db.commit()

    @staticmethod
    def update(db: Session, employee: Employee, **fields: Any) -> Employee:
        for key, value in fields.items():
            setattr(employee, key, value)
        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def update_status(db: Session, employee: Employee, status: str) -> Employee:
        employee.employee_status = status.strip()
        db.commit()
        db.refresh(employee)
        return employee
