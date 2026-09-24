from sqlalchemy.orm import Session

from app.schemas.floor import FloorCreate, FloorResponse, FloorUpdate
from app.services.floor_service import FloorService


class FloorController:
    @staticmethod
    def list_floors(
        db: Session, building_id: int | None = None
    ) -> list[FloorResponse]:
        return FloorService.list_floors(db, building_id=building_id)

    @staticmethod
    def get_floor(db: Session, floor_id: int) -> FloorResponse:
        return FloorService.get_floor_response(db, floor_id)

    @staticmethod
    def create_floor(db: Session, data: FloorCreate) -> FloorResponse:
        return FloorService.create_floor(db, data)

    @staticmethod
    def update_floor(
        db: Session, floor_id: int, data: FloorUpdate
    ) -> FloorResponse:
        return FloorService.update_floor(db, floor_id, data)

    @staticmethod
    def delete_floor(db: Session, floor_id: int) -> dict[str, str]:
        return FloorService.delete_floor(db, floor_id)
