import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import EMPLOYEE_STATUS_ACTIVE

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class EmployeeBase(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    phone: str | None = Field(None, max_length=20)
    designation: str = Field(..., min_length=1, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    employment_type: str = Field(..., min_length=1, max_length=30)
    employee_status: str = Field(default=EMPLOYEE_STATUS_ACTIVE, max_length=30)
    manager_id: int | None = None
    team_id: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email format: '{v}'")
        return clean


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    employee_code: str | None = Field(None, min_length=1, max_length=50)
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, min_length=3, max_length=255)
    phone: str | None = Field(None, max_length=20)
    designation: str | None = Field(None, min_length=1, max_length=100)
    department: str | None = Field(None, min_length=1, max_length=100)
    employment_type: str | None = Field(None, min_length=1, max_length=30)
    employee_status: str | None = Field(None, max_length=30)
    manager_id: int | None = None
    team_id: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email_opt(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email format: '{v}'")
        return clean


class EmployeeStatusUpdate(BaseModel):
    employee_status: str = Field(..., max_length=30)


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    manager_name: str | None = None
    team_name: str | None = None
    is_user_linked: bool = False


class CSVRowError(BaseModel):
    row: int
    field: str
    message: str


class CSVImportSummaryResponse(BaseModel):
    total_rows: int
    imported_count: int
    failed_count: int
    errors: list[CSVRowError] = []
