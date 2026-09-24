from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserManagementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    sso_user_id: str | None = None
    role_id: int
    role_name: str
    employee_id: int | None = None
    employee_name: str | None = None
    employee_code: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserEmployeeAssignRequest(BaseModel):
    employee_id: int | None = None


class UserRoleUpdateRequest(BaseModel):
    role_name: str


class UserStatusUpdateRequest(BaseModel):
    is_active: bool


class UserProvisionRequest(BaseModel):
    employee_id: int
    sso_user_id: str
    role_name: str = "Employee"
    email: str | None = None


class CSVUserRowError(BaseModel):
    row: int
    field: str
    message: str


class UserProvisionCSVResponse(BaseModel):
    total_rows: int
    imported_count: int
    failed_count: int
    errors: list[CSVUserRowError]
