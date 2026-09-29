from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class SeatBase(BaseModel):
    seat_number: str = Field(..., max_length=50)
    seat_type: str = Field("Standard", max_length=30)
    status: str = Field("Vacant", max_length=30)
    x_position: float = Field(0.0, ge=0)
    y_position: float = Field(0.0, ge=0)

class SeatCreate(SeatBase):
    floor_id: int

class SeatBatchCreate(BaseModel):
    floor_id: int
    count: int = Field(..., ge=1, le=100)
    prefix: str = Field("S-", max_length=20)
    start_number: int | None = Field(None, ge=1)
    seat_type: str = Field("Standard", max_length=30)

class SeatUpdate(BaseModel):
    seat_number: str | None = Field(None, max_length=50)
    seat_type: str | None = Field(None, max_length=30)
    status: str | None = Field(None, max_length=30)
    x_position: float | None = Field(None, ge=0)
    y_position: float | None = Field(None, ge=0)

class SeatAssignRequest(BaseModel):
    employee_id: int
    notes: str | None = None

class SeatRelocateRequest(BaseModel):
    current_seat_id: int
    target_seat_id: int
    notes: str | None = None

class SeatSwapRequest(BaseModel):
    seat_id: int
    target_employee_id: int
    notes: str | None = None

class SeatReleaseRequest(BaseModel):
    notes: str | None = None

class SeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    floor_id: int
    seat_number: str
    seat_type: str
    status: str
    x_position: float
    y_position: float
    employee_id: int | None = None
    employee_name: str | None = None
    employee_code: str | None = None
    employee_email: str | None = None
    building_id: int | None = None
    building_name: str | None = None
    floor_name: str | None = None
    floor_number: int | None = None

class FloorSummaryItem(BaseModel):
    floor_id: int
    floor_name: str
    floor_number: int
    total_seats: int
    occupied_seats: int
    vacant_seats: int

class BuildingSeatingSummary(BaseModel):
    building_id: int
    building_name: str
    total_seats: int
    occupied_seats: int
    vacant_seats: int
    floors: list[FloorSummaryItem]

class RoleDistributionItem(BaseModel):
    role_name: str
    count: int
    percent: str

class SeatingOverviewResponse(BaseModel):
    total_seats: int
    total_occupied: int
    total_vacant: int
    total_blocked: int
    buildings: list[BuildingSeatingSummary]
    role_distribution: list[RoleDistributionItem] = []

class FloorSeatingMapResponse(BaseModel):
    floor_id: int
    floor_name: str
    floor_number: int
    building_id: int
    building_name: str
    map_width: int
    map_height: int
    total_seats: int
    occupied_seats: int
    vacant_seats: int
    blocked_seats: int
    seats: list[SeatResponse]

class SeatHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seat_id: int
    seat_number: str
    employee_id: int | None = None
    employee_name: str | None = None
    employee_code: str | None = None
    action: str
    previous_status: str | None = None
    new_status: str | None = None
    action_date: datetime
