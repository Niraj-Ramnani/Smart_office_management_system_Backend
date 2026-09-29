from sqlalchemy.orm import Session

from app.schemas.floor import FloorCreate, FloorResponse, FloorUpdate
from app.services.floor_service import FloorService
from app.services.notification_service import ws_manager

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
        res = FloorService.create_floor(db, data)
        ws_manager.broadcast_entity_change("Floor", "created", ["Floor", "Building", "Seat"])
        return res

    @staticmethod
    def update_floor(
        db: Session, floor_id: int, data: FloorUpdate
    ) -> FloorResponse:
        res = FloorService.update_floor(db, floor_id, data)
        ws_manager.broadcast_entity_change("Floor", "updated", ["Floor", "Building", "Seat"])
        return res

    @staticmethod
    def delete_floor(db: Session, floor_id: int) -> dict[str, str]:
        res = FloorService.delete_floor(db, floor_id)
        ws_manager.broadcast_entity_change("Floor", "deleted", ["Floor", "Building", "Seat"])
        return res
