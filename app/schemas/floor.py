from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DEFAULT_MAP_HEIGHT, DEFAULT_MAP_WIDTH


class FloorBase(BaseModel):
    building_id: int
    name: str = Field(..., min_length=1, max_length=100)
    floor_number: int
    map_width: int = Field(default=DEFAULT_MAP_WIDTH, ge=100, le=10000)
    map_height: int = Field(default=DEFAULT_MAP_HEIGHT, ge=100, le=10000)


class FloorCreate(FloorBase):
    pass


class FloorUpdate(BaseModel):
    building_id: int | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    floor_number: int | None = None
    map_width: int | None = Field(None, ge=100, le=10000)
    map_height: int | None = Field(None, ge=100, le=10000)


class FloorResponse(FloorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    building_name: str | None = None
    seat_count: int = 0
