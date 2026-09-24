from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers.floor_controller import FloorController
from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.floor import FloorCreate, FloorResponse, FloorUpdate

router = APIRouter(prefix="/floors", tags=["Floors"])


@router.get("", response_model=list[FloorResponse])
def list_floors(
    building_id: int | None = Query(None, description="Filter by building ID"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[FloorResponse]:
    return FloorController.list_floors(db, building_id=building_id)


@router.get("/{floor_id}", response_model=FloorResponse)
def get_floor(
    floor_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FloorResponse:
    return FloorController.get_floor(db, floor_id)


@router.post("", response_model=FloorResponse, status_code=status.HTTP_201_CREATED)
def create_floor(
    data: FloorCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> FloorResponse:
    return FloorController.create_floor(db, data)


@router.put("/{floor_id}", response_model=FloorResponse)
def update_floor(
    floor_id: int,
    data: FloorUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> FloorResponse:
    return FloorController.update_floor(db, floor_id, data)


@router.delete("/{floor_id}")
def delete_floor(
    floor_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    return FloorController.delete_floor(db, floor_id)
