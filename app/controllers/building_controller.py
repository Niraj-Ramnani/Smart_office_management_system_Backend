from sqlalchemy.orm import Session

from app.schemas.building import BuildingCreate, BuildingResponse, BuildingUpdate
from app.services.building_service import BuildingService


class BuildingController:
    @staticmethod
    def list_buildings(db: Session) -> list[BuildingResponse]:
        return BuildingService.list_buildings(db)

    @staticmethod
    def get_building(db: Session, building_id: int) -> BuildingResponse:
        return BuildingService.get_building_response(db, building_id)

    @staticmethod
    def create_building(db: Session, data: BuildingCreate) -> BuildingResponse:
        return BuildingService.create_building(db, data)

    @staticmethod
    def update_building(
        db: Session, building_id: int, data: BuildingUpdate
    ) -> BuildingResponse:
        return BuildingService.update_building(db, building_id, data)

    @staticmethod
    def delete_building(db: Session, building_id: int) -> dict[str, str]:
        return BuildingService.delete_building(db, building_id)
