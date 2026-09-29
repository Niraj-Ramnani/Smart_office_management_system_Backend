from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class SeatRequestCreate(BaseModel):
    request_type: str = Field(..., max_length=30)
    preferred_seat_id: int | None = None
    target_seat_id: int | None = None
    target_employee_id: int | None = None
    asset_type: str | None = None
    current_asset_id: int | None = None
    employee_id: int | None = None
    reason: str | None = None

class SeatRequestReview(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    rejected_reason: str | None = None

class SwapConsentAction(BaseModel):
    action: str = Field(..., pattern="^(ACCEPT|REJECT)$")

class SeatRequestExecute(BaseModel):
    seat_id: int | None = None
    asset_id: int | None = None
    replacement_asset_id: int | None = None
    notes: str | None = None

class SeatRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: str | None = None
    employee_code: str | None = None
    employee_email: str | None = None
    department: str | None = None
    request_type: str
    status: str
    requested_for: datetime | None = None
    details: dict[str, Any] | None = None
    approved_by: int | None = None
    approver_name: str | None = None
    approved_at: datetime | None = None
    assigned_to: int | None = None
    executor_name: str | None = None
    completed_at: datetime | None = None
    rejected_reason: str | None = None
    created_at: datetime
    updated_at: datetime
