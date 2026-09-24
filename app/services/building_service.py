from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.building import Building
from app.repositories.building_repository import BuildingRepository
from app.schemas.building import BuildingCreate, BuildingResponse, BuildingUpdate


class BuildingService:
    @staticmethod
    def list_buildings(db: Session) -> list[BuildingResponse]:
        buildings = BuildingRepository.get_all(db)
        result = []
        for b in buildings:
            res = BuildingResponse.model_validate(b)
            res.floor_count = len(b.floors) if b.floors else 0
            result.append(res)
        return result

    @staticmethod
    def get_building(db: Session, building_id: int) -> Building:
        building = BuildingRepository.get_by_id(db, building_id)
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID {building_id} not found",
            )
        return building

    @staticmethod
    def get_building_response(db: Session, building_id: int) -> BuildingResponse:
        building = BuildingService.get_building(db, building_id)
        res = BuildingResponse.model_validate(building)
        res.floor_count = len(building.floors) if building.floors else 0
        return res

    @staticmethod
    def create_building(db: Session, data: BuildingCreate) -> BuildingResponse:
        code_clean = data.code.strip()
        existing = BuildingRepository.get_by_code(db, code_clean)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Building with code '{code_clean}' already exists",
            )

        building = BuildingRepository.create(
            db,
            name=data.name.strip(),
            code=code_clean,
            address=data.address.strip() if data.address else None,
        )
        res = BuildingResponse.model_validate(building)
        res.floor_count = 0
        return res

    @staticmethod
    def update_building(
        db: Session, building_id: int, data: BuildingUpdate
    ) -> BuildingResponse:
        building = BuildingService.get_building(db, building_id)

        code_to_update = None
        if data.code is not None:
            code_clean = data.code.strip()
            conflict = BuildingRepository.get_by_code(
                db, code_clean, exclude_id=building_id
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Building code '{code_clean}' is already in use",
                )
            code_to_update = code_clean

        name_to_update = data.name.strip() if data.name is not None else None
        address_to_update = data.address.strip() if data.address is not None else None

        updated = BuildingRepository.update(
            db,
            building,
            name=name_to_update,
            code=code_to_update,
            address=address_to_update,
        )

        res = BuildingResponse.model_validate(updated)
        res.floor_count = len(updated.floors) if updated.floors else 0
        return res

    @staticmethod
    def delete_building(db: Session, building_id: int) -> dict[str, str]:
        building = BuildingService.get_building(db, building_id)
        if building.floors and len(building.floors) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete building '{building.name}' because it contains active floors.",
            )
        BuildingRepository.delete(db, building)
        return {"message": f"Building '{building.name}' deleted successfully"}
