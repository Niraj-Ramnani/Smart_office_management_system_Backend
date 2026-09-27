from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.seat_request import (
    SeatRequestCreate,
    SeatRequestExecute,
    SeatRequestResponse,
    SeatRequestReview,
    SwapConsentAction,
)
from app.services.seat_request_service import SeatRequestService


class SeatRequestController:
    @staticmethod
    def create_request(
        db: Session,
        current_user: User,
        data: SeatRequestCreate,
    ) -> SeatRequestResponse:
        return SeatRequestService.create_request(db, current_user, data)

    @staticmethod
    def get_my_requests(
        db: Session,
        current_user: User,
    ) -> list[SeatRequestResponse]:
        return SeatRequestService.get_my_requests(db, current_user)

    @staticmethod
    def get_manager_requests(
        db: Session,
        current_user: User,
        status_filter: str | None = None,
    ) -> list[SeatRequestResponse]:
        return SeatRequestService.get_manager_requests(db, current_user, status_filter)

    @staticmethod
    def get_all_requests(
        db: Session,
        status_filter: str | None = None,
        request_type: str | None = None,
    ) -> list[SeatRequestResponse]:
        return SeatRequestService.get_all_requests(db, status_filter, request_type)

    @staticmethod
    def get_approved_for_admin(db: Session) -> list[SeatRequestResponse]:
        return SeatRequestService.get_approved_for_admin(db)

    @staticmethod
    def review_request(
        db: Session,
        request_id: int,
        current_user: User,
        data: SeatRequestReview,
    ) -> SeatRequestResponse:
        return SeatRequestService.review_request(db, request_id, current_user, data)

    @staticmethod
    def respond_swap_consent(
        db: Session,
        request_id: int,
        current_user: User,
        data: SwapConsentAction,
    ) -> SeatRequestResponse:
        return SeatRequestService.respond_swap_consent(db, request_id, current_user, data)

    @staticmethod
    def execute_request(
        db: Session,
        request_id: int,
        current_user: User,
        data: SeatRequestExecute,
    ) -> SeatRequestResponse:
        return SeatRequestService.execute_request(db, request_id, current_user, data)
