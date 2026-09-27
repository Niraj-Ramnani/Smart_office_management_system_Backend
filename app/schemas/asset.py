from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class AssetCreate(BaseModel):
    asset_code: str = Field(..., max_length=50)
    asset_type: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    serial_number: str = Field(..., max_length=100)
    purchase_date: date | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    purchase_date: date | None = None


class AssetAllocate(BaseModel):
    employee_id: int
    notes: str | None = None


class AssetReturn(BaseModel):
    notes: str | None = None


class AssetMaintenance(BaseModel):
    notes: str | None = None


class AssetReplace(BaseModel):
    replacement_asset_id: int
    notes: str | None = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    asset_type: str
    name: str
    serial_number: str
    status: str
    purchase_date: date | None = None
    created_at: datetime
    updated_at: datetime
    current_employee_id: int | None = None
    current_employee_name: str | None = None
    current_employee_code: str | None = None


class AssetAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    employee_id: int
    action: str
    allocated_at: datetime
    returned_at: datetime | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    asset_code: str | None = None
    asset_type: str | None = None
    asset_name: str | None = None
    employee_name: str | None = None
    employee_code: str | None = None
