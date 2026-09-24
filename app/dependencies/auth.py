import logging
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi_azure_auth.user import User as AzureUser
from sqlalchemy.orm import Session, joinedload

from app.core.auth import azure_scheme
from app.core.constants import ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER
from app.db.dependencies import get_db
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
        .options(joinedload(User.role))
        .filter(User.sso_user_id == oid)
        .first()
    )

    if not user:
        email = (
            azure_user.claims.get("email")
            or azure_user.claims.get("preferred_username")
            or azure_user.claims.get("upn")
            or "Unknown"
        )
        logger.warning("User not registered: oid='%s', email='%s'", oid, email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not registered",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
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
