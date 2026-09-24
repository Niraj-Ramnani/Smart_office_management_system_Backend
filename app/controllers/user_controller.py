from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.schemas.user_management import (
    RoleResponse,
    UserEmployeeAssignRequest,
    UserManagementResponse,
    UserProvisionCSVResponse,
    UserProvisionRequest,
    UserRoleUpdateRequest,
    UserStatusUpdateRequest,
)
from app.services.user_service import UserService


class UserController:
    @staticmethod
    def list_users(db: Session) -> list[UserManagementResponse]:
        return UserService.list_users(db)

    @staticmethod
    def list_roles(db: Session) -> list[RoleResponse]:
        return UserService.list_roles(db)

    @staticmethod
    def assign_user_employee(
        db: Session, user_id: int, data: UserEmployeeAssignRequest
    ) -> UserManagementResponse:
        return UserService.assign_user_employee(db, user_id, data.employee_id)

    @staticmethod
    def update_user_role(
        db: Session, user_id: int, data: UserRoleUpdateRequest
    ) -> UserManagementResponse:
        return UserService.update_user_role(db, user_id, data.role_name)

    @staticmethod
    def update_user_status(
        db: Session, user_id: int, data: UserStatusUpdateRequest
    ) -> UserManagementResponse:
        return UserService.update_user_status(db, user_id, data.is_active)

    @staticmethod
    def provision_user(
        db: Session, data: UserProvisionRequest
    ) -> UserManagementResponse:
        return UserService.provision_user(db, data)

    @staticmethod
    async def provision_users_csv(
        request: Request, db: Session
    ) -> UserProvisionCSVResponse:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            content_str = body.get("csv_content", "")
        else:
            body_bytes = await request.body()
            try:
                content_str = body_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                content_str = body_bytes.decode("latin-1", errors="replace")

        if not content_str.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV content is empty",
            )

        return UserService.provision_users_csv(db, content_str)
