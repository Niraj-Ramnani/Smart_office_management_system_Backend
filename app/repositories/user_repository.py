from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.role import Role
from app.models.user import User


class UserRepository:
    @staticmethod
    def get_all(db: Session) -> list[User]:
        return (
            db.query(User)
            .options(joinedload(User.role), joinedload(User.employee))
            .order_by(User.id)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        return (
            db.query(User)
            .options(joinedload(User.role), joinedload(User.employee))
            .filter(User.id == user_id)
            .first()
        )

    @staticmethod
    def get_by_employee_id(
        db: Session, employee_id: int, exclude_user_id: int | None = None
    ) -> User | None:
        query = db.query(User).filter(User.employee_id == employee_id)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return query.first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return (
            db.query(User)
            .options(joinedload(User.role), joinedload(User.employee))
            .filter(func.lower(User.email) == email.strip().lower())
            .first()
        )

    @staticmethod
    def get_by_sso_id(db: Session, sso_id: str) -> User | None:
        return (
            db.query(User)
            .options(joinedload(User.role), joinedload(User.employee))
            .filter(User.sso_user_id == sso_id.strip())
            .first()
        )

    @staticmethod
    def get_all_emails_set(db: Session) -> set[str]:
        return {email.lower() for (email,) in db.query(User.email).all()}

    @staticmethod
    def get_all_sso_ids_set(db: Session) -> set[str]:
        return {sso_id.lower() for (sso_id,) in db.query(User.sso_user_id).filter(User.sso_user_id.isnot(None)).all()}

    @staticmethod
    def get_all_linked_employee_ids_set(db: Session) -> set[int]:
        return {emp_id for (emp_id,) in db.query(User.employee_id).filter(User.employee_id.isnot(None)).all()}

    @staticmethod
    def get_roles(db: Session) -> list[Role]:
        return db.query(Role).order_by(Role.id).all()

    @staticmethod
    def get_role_by_name(db: Session, role_name: str) -> Role | None:
        return (
            db.query(Role)
            .filter(func.lower(Role.name) == role_name.strip().lower())
            .first()
        )

    @staticmethod
    def update_employee_link(
        db: Session, user: User, employee_id: int | None
    ) -> User:
        user.employee_id = employee_id
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_role(db: Session, user: User, role_id: int) -> User:
        user.role_id = role_id
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_status(db: Session, user: User, is_active: bool) -> User:
        user.is_active = is_active
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def create(
        db: Session,
        email: str,
        sso_user_id: str,
        role_id: int,
        employee_id: int,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            sso_user_id=sso_user_id.strip(),
            role_id=role_id,
            employee_id=employee_id,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def bulk_create(db: Session, user_dicts: list[dict]) -> list[User]:
        users = [
            User(
                email=u["email"].strip().lower(),
                sso_user_id=u["sso_user_id"].strip(),
                role_id=u["role_id"],
                employee_id=u["employee_id"],
                is_active=u.get("is_active", True),
            )
            for u in user_dicts
        ]
        db.add_all(users)
        db.commit()
        for u in users:
            db.refresh(u)
        return users
