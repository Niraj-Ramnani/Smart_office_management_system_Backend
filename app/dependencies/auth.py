import logging
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi_azure_auth.user import User as AzureUser
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.auth import azure_scheme
from app.core.constants import ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER
from app.db.dependencies import get_db
from app.models.employee import Employee
from app.models.role import Role
from app.models.user import User

logger = logging.getLogger("uvicorn.error")


def get_current_user(
    azure_user: AzureUser = Depends(azure_scheme),
    db: Session = Depends(get_db),
) -> User:
    oid: str | None = azure_user.claims.get("oid")
    if not oid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain user object identifier (oid)",
        )

    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.employee))
        .filter(User.sso_user_id == oid)
        .first()
    )

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        if user.employee and user.employee.employee_status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your employee record is inactive. Please contact your administrator.",
            )
        return user

    raw_email = (
        azure_user.claims.get("email")
        or azure_user.claims.get("preferred_username")
        or azure_user.claims.get("upn")
        or ""
    )
    email_clean = raw_email.strip().lower()
    if not email_clean:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your Microsoft account is authenticated, but you are not registered as an employee in the application. Please contact the administrator.",
        )

    employee = (
        db.query(Employee)
        .filter(func.lower(Employee.email) == email_clean)
        .first()
    )

    if not employee:
        logger.warning("Unregistered employee login attempt: oid='%s', email='%s'", oid, email_clean)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your Microsoft account is authenticated, but you are not registered as an employee in the application. Please contact the administrator.",
        )

    if employee.employee_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your employee record is inactive. Please contact your administrator.",
        )

    existing_user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.employee))
        .filter((User.employee_id == employee.id) | (func.lower(User.email) == email_clean))
        .first()
    )

    if existing_user:
        if existing_user.sso_user_id and existing_user.sso_user_id != oid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account conflict: this employee is already associated with another identity.",
            )
        if not existing_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        existing_user.sso_user_id = oid
        existing_user.employee_id = employee.id
        db.commit()
        db.refresh(existing_user)
        return existing_user

    role = db.query(Role).filter(Role.name == ROLE_EMPLOYEE).first()
    if not role:
        role = Role(name=ROLE_EMPLOYEE, description="Standard employee access")
        db.add(role)
        db.flush()

    new_user = User(
        email=employee.email,
        sso_user_id=oid,
        role_id=role.id,
        employee_id=employee.id,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.employee))
        .filter(User.id == new_user.id)
        .first()
    )
    return user


class RoleChecker:
    def __init__(self, *allowed_roles: str) -> None:
        self.allowed_roles = set(allowed_roles)

    def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        role_name = current_user.role.name if current_user.role else ""
        if role_name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user


def require_role(*roles: str) -> Callable[..., Any]:
    return RoleChecker(*roles)


require_admin = require_role(ROLE_ADMIN)
require_manager = require_role(ROLE_MANAGER)
require_employee = require_role(ROLE_EMPLOYEE)
