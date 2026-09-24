from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.controllers.user_controller import UserController
from app.db.dependencies import get_db
from app.dependencies.auth import require_admin
from app.models.user import User
from app.schemas.user_management import (
    RoleResponse,
    UserEmployeeAssignRequest,
    UserManagementResponse,
    UserProvisionCSVResponse,
    UserProvisionRequest,
    UserRoleUpdateRequest,
    UserStatusUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["Users & Role Management"])


@router.get("", response_model=list[UserManagementResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserManagementResponse]:
    return UserController.list_users(db)


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[RoleResponse]:
    return UserController.list_roles(db)


@router.post("/provision", response_model=UserManagementResponse, status_code=status.HTTP_201_CREATED)
def provision_user(
    data: UserProvisionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserManagementResponse:
    return UserController.provision_user(db, data)


@router.post("/provision/csv", response_model=UserProvisionCSVResponse)
async def provision_users_csv(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserProvisionCSVResponse:
    return await UserController.provision_users_csv(request, db)


@router.patch("/{user_id}/employee", response_model=UserManagementResponse)
def assign_user_employee(
    user_id: int,
    data: UserEmployeeAssignRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserManagementResponse:
    return UserController.assign_user_employee(db, user_id, data)


@router.patch("/{user_id}/role", response_model=UserManagementResponse)
def update_user_role(
    user_id: int,
    data: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserManagementResponse:
    return UserController.update_user_role(db, user_id, data)


@router.patch("/{user_id}/status", response_model=UserManagementResponse)
def update_user_status(
    user_id: int,
    data: UserStatusUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserManagementResponse:
    return UserController.update_user_status(db, user_id, data)
