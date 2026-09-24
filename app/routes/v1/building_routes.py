from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.building_controller import BuildingController
from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.building import BuildingCreate, BuildingResponse, BuildingUpdate

router = APIRouter(prefix="/buildings", tags=["Buildings"])


@router.get("", response_model=list[BuildingResponse])
def list_buildings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[BuildingResponse]:
    return BuildingController.list_buildings(db)


@router.get("/{building_id}", response_model=BuildingResponse)
def get_building(
    building_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> BuildingResponse:
    return BuildingController.get_building(db, building_id)


@router.post("", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
def create_building(
    data: BuildingCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BuildingResponse:
    return BuildingController.create_building(db, data)


@router.put("/{building_id}", response_model=BuildingResponse)
def update_building(
    building_id: int,
    data: BuildingUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BuildingResponse:
    return BuildingController.update_building(db, building_id, data)


@router.delete("/{building_id}")
def delete_building(
    building_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    return BuildingController.delete_building(db, building_id)
