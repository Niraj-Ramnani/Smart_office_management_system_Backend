from sqlalchemy.orm import Session

from app.schemas.building import BuildingCreate, BuildingResponse, BuildingUpdate
from app.services.building_service import BuildingService
from app.services.notification_service import ws_manager

class BuildingController:
    @staticmethod
    def list_buildings(db: Session) -> list[BuildingResponse]:
        return BuildingService.list_buildings(db)

    @staticmethod
    def get_building(db: Session, building_id: int) -> BuildingResponse:
        return BuildingService.get_building_response(db, building_id)

    @staticmethod
    def create_building(db: Session, data: BuildingCreate) -> BuildingResponse:
        res = BuildingService.create_building(db, data)
        ws_manager.broadcast_entity_change("Building", "created", ["Building", "Floor", "Seat"])
        return res

    @staticmethod
    def update_building(
        db: Session, building_id: int, data: BuildingUpdate
    ) -> BuildingResponse:
        res = BuildingService.update_building(db, building_id, data)
        ws_manager.broadcast_entity_change("Building", "updated", ["Building", "Floor", "Seat"])
        return res

    @staticmethod
    def delete_building(db: Session, building_id: int) -> dict[str, str]:
        res = BuildingService.delete_building(db, building_id)
        ws_manager.broadcast_entity_change("Building", "deleted", ["Building", "Floor", "Seat"])
        return res
