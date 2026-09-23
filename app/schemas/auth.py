from pydantic import BaseModel, ConfigDict


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    employee_id: int | None = None
    role: str
    is_active: bool
