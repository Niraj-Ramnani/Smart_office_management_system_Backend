from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.floor import Floor
from app.repositories.building_repository import BuildingRepository
from app.repositories.floor_repository import FloorRepository
from app.schemas.floor import FloorCreate, FloorResponse, FloorUpdate


class FloorService:
    @staticmethod
    def list_floors(
        db: Session, building_id: int | None = None
    ) -> list[FloorResponse]:
        floors = FloorRepository.get_all(db, building_id=building_id)
        result = []
        for f in floors:
            res = FloorResponse.model_validate(f)
            res.building_name = f.building.name if f.building else None
            res.seat_count = len(f.seats) if f.seats else 0
            result.append(res)
        return result

    @staticmethod
    def get_floor(db: Session, floor_id: int) -> Floor:
        floor = FloorRepository.get_by_id(db, floor_id)
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID {floor_id} not found",
            )
        return floor

    @staticmethod
    def get_floor_response(db: Session, floor_id: int) -> FloorResponse:
        floor = FloorService.get_floor(db, floor_id)
        res = FloorResponse.model_validate(floor)
        res.building_name = floor.building.name if floor.building else None
        res.seat_count = len(floor.seats) if floor.seats else 0
        return res

    @staticmethod
    def create_floor(db: Session, data: FloorCreate) -> FloorResponse:
        building = BuildingRepository.get_by_id(db, data.building_id)
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID {data.building_id} not found",
            )

        conflict = FloorRepository.get_by_building_and_number(
            db, data.building_id, data.floor_number
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Floor number {data.floor_number} already exists in this building",
            )

        floor = FloorRepository.create(
            db,
            building_id=data.building_id,
            name=data.name.strip(),
            floor_number=data.floor_number,
            map_width=data.map_width,
            map_height=data.map_height,
        )

        res = FloorResponse.model_validate(floor)
        res.building_name = floor.building.name if floor.building else None
        res.seat_count = 0
        return res

    @staticmethod
    def update_floor(
        db: Session, floor_id: int, data: FloorUpdate
    ) -> FloorResponse:
        floor = FloorService.get_floor(db, floor_id)

        target_building_id = (
            data.building_id if data.building_id is not None else floor.building_id
        )
        target_floor_num = (
            data.floor_number
            if data.floor_number is not None
            else floor.floor_number
        )

        if data.building_id is not None and data.building_id != floor.building_id:
            building = BuildingRepository.get_by_id(db, data.building_id)
            if not building:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Building with ID {data.building_id} not found",
                )

        if (
            target_building_id != floor.building_id
            or target_floor_num != floor.floor_number
        ):
            conflict = FloorRepository.get_by_building_and_number(
                db, target_building_id, target_floor_num, exclude_id=floor_id
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Floor number {target_floor_num} already exists in target building",
                )

        updated = FloorRepository.update(
            db,
            floor,
            building_id=data.building_id,
            name=data.name.strip() if data.name is not None else None,
            floor_number=data.floor_number,
            map_width=data.map_width,
            map_height=data.map_height,
        )

        res = FloorResponse.model_validate(updated)
        res.building_name = updated.building.name if updated.building else None
        res.seat_count = len(updated.seats) if updated.seats else 0
        return res

    @staticmethod
    def delete_floor(db: Session, floor_id: int) -> dict[str, str]:
        floor = FloorService.get_floor(db, floor_id)
        if floor.seats and len(floor.seats) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete floor '{floor.name}' because seats reference this floor.",
            )
        FloorRepository.delete(db, floor)
        return {"message": f"Floor '{floor.name}' deleted successfully"}
