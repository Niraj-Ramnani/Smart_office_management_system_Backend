from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers.seat_controller import SeatController
from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.seat import (
    FloorSeatingMapResponse,
    SeatAssignRequest,
    SeatBatchCreate,
    SeatCreate,
    SeatHistoryResponse,
    SeatReleaseRequest,
    SeatRelocateRequest,
    SeatResponse,
    SeatSwapRequest,
    SeatUpdate,
    SeatingOverviewResponse,
)

router = APIRouter(prefix="/seats", tags=["Seat Management"])

@router.get("/overview", response_model=SeatingOverviewResponse)
def get_seating_overview(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SeatingOverviewResponse:
    return SeatController.get_seating_overview(db)

@router.get("/floor-map/{floor_id}", response_model=FloorSeatingMapResponse)
def get_floor_seating_map(
    floor_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FloorSeatingMapResponse:
    return SeatController.get_floor_seating_map(db, floor_id)

@router.get("", response_model=list[SeatResponse])
def list_seats(
    floor_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SeatResponse]:
    return SeatController.list_seats(db, floor_id=floor_id, seat_status=status)

@router.get("/{seat_id}", response_model=SeatResponse)
def get_seat(
    seat_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SeatResponse:
    return SeatController.get_seat(db, seat_id)

@router.post("", response_model=SeatResponse, status_code=status.HTTP_201_CREATED)
def create_seat(
    data: SeatCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> SeatResponse:
    return SeatController.create_seat(db, data)

@router.post("/batch", response_model=list[SeatResponse], status_code=status.HTTP_201_CREATED)
def batch_create_seats(
    data: SeatBatchCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[SeatResponse]:
    return SeatController.batch_create_seats(db, data)

@router.put("/{seat_id}", response_model=SeatResponse)
def update_seat(
    seat_id: int,
    data: SeatUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> SeatResponse:
    return SeatController.update_seat(db, seat_id, data)

@router.delete("/{seat_id}")
def delete_seat(
    seat_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    return SeatController.delete_seat(db, seat_id)

@router.post("/{seat_id}/assign", response_model=SeatResponse)
def assign_seat(
    seat_id: int,
    data: SeatAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SeatResponse:
    return SeatController.assign_seat(db, seat_id, data, current_user.id)

@router.post("/{seat_id}/release", response_model=SeatResponse)
def release_seat(
    seat_id: int,
    data: SeatReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SeatResponse:
    return SeatController.release_seat(db, seat_id, data, current_user.id)

@router.post("/relocate", response_model=SeatResponse)
def relocate_seat(
    data: SeatRelocateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SeatResponse:
    return SeatController.relocate_seat(db, data, current_user.id)

@router.post("/swap", response_model=list[SeatResponse])
def swap_seats(
    data: SeatSwapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[SeatResponse]:
    return SeatController.swap_seats(db, data, current_user.id)

@router.get("/{seat_id}/history", response_model=list[SeatHistoryResponse])
def get_seat_history(
    seat_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SeatHistoryResponse]:
    return SeatController.get_seat_history(db, seat_id)

@router.get("/employee/{employee_id}/history", response_model=list[SeatHistoryResponse])
def get_employee_seat_history(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SeatHistoryResponse]:
    return SeatController.get_employee_seat_history(db, employee_id)
