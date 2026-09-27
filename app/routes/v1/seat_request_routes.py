from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers.seat_request_controller import SeatRequestController
from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.seat_request import (
    SeatRequestCreate,
    SeatRequestExecute,
    SeatRequestResponse,
    SeatRequestReview,
    SwapConsentAction,
)

router = APIRouter(prefix="/seat-requests", tags=["Seat & Asset Request Workflow"])


@router.post("", response_model=SeatRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    data: SeatRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SeatRequestResponse:
    return SeatRequestController.create_request(db, current_user, data)


@router.get("/my", response_model=list[SeatRequestResponse])
def get_my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SeatRequestResponse]:
    return SeatRequestController.get_my_requests(db, current_user)


@router.get("/team", response_model=list[SeatRequestResponse])
def get_team_requests(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SeatRequestResponse]:
    return SeatRequestController.get_manager_requests(db, current_user, status)


@router.get("", response_model=list[SeatRequestResponse])
def get_all_requests(
    status: str | None = Query(None),
    request_type: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[SeatRequestResponse]:
    return SeatRequestController.get_all_requests(db, status, request_type)


@router.get("/approved", response_model=list[SeatRequestResponse])
def get_approved_for_admin(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[SeatRequestResponse]:
    return SeatRequestController.get_approved_for_admin(db)


@router.post("/{request_id}/review", response_model=SeatRequestResponse)
def review_request(
    request_id: int,
    data: SeatRequestReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SeatRequestResponse:
    return SeatRequestController.review_request(db, request_id, current_user, data)


@router.post("/{request_id}/respond-swap", response_model=SeatRequestResponse)
def respond_swap_consent(
    request_id: int,
    data: SwapConsentAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SeatRequestResponse:
    return SeatRequestController.respond_swap_consent(db, request_id, current_user, data)


@router.post("/{request_id}/execute", response_model=SeatRequestResponse)
def execute_request(
    request_id: int,
    data: SeatRequestExecute,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SeatRequestResponse:
    return SeatRequestController.execute_request(db, request_id, current_user, data)
