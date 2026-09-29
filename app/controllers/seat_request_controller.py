from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.seat_request import (
    SeatRequestCreate,
    SeatRequestExecute,
    SeatRequestResponse,
    SeatRequestReview,
    SwapConsentAction,
)
from app.services.notification_service import ws_manager
from app.services.seat_request_service import SeatRequestService

class SeatRequestController:
    @staticmethod
    def create_request(
        db: Session,
        current_user: User,
        data: SeatRequestCreate,
    ) -> SeatRequestResponse:
        res = SeatRequestService.create_request(db, current_user, data)
        ws_manager.broadcast_entity_change("SeatRequest", "created", ["SeatRequest", "Notification"])
        return res

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
        res = SeatRequestService.review_request(db, request_id, current_user, data)
        ws_manager.broadcast_entity_change("SeatRequest", "reviewed", ["SeatRequest", "Notification"])
        return res

    @staticmethod
    def respond_swap_consent(
        db: Session,
        request_id: int,
        current_user: User,
        data: SwapConsentAction,
    ) -> SeatRequestResponse:
        res = SeatRequestService.respond_swap_consent(db, request_id, current_user, data)
        ws_manager.broadcast_entity_change("SeatRequest", "consented", ["SeatRequest", "Notification"])
        return res

    @staticmethod
    def execute_request(
        db: Session,
        request_id: int,
        current_user: User,
        data: SeatRequestExecute,
    ) -> SeatRequestResponse:
        res = SeatRequestService.execute_request(db, request_id, current_user, data)
        ws_manager.broadcast_entity_change("SeatRequest", "executed", ["SeatRequest", "Seat", "Employee", "Asset", "Notification"])
        return res
