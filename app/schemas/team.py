from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    manager_id: int

class TeamCreate(TeamBase):
    pass

class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    department: str | None = Field(None, min_length=1, max_length=100)
    manager_id: int | None = None

class TeamMemberItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    designation: str
    department: str
    employee_status: str
    seat_number: str | None = None

class TeamMemberAddRequest(BaseModel):
    employee_ids: list[int] = Field(..., min_length=1)

class TeamResponse(TeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    manager_name: str | None = None
    manager_email: str | None = None
    manager_designation: str | None = None
    manager_employee_code: str | None = None
    manager_seat_number: str | None = None
    member_count: int = 0
    members: list[TeamMemberItem] = []
