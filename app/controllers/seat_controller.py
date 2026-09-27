from sqlalchemy.orm import Session

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
from app.services.seat_service import SeatService


class SeatController:
    @staticmethod
    def get_seating_overview(db: Session) -> SeatingOverviewResponse:
        return SeatService.get_seating_overview(db)

    @staticmethod
    def get_floor_seating_map(db: Session, floor_id: int) -> FloorSeatingMapResponse:
        return SeatService.get_floor_seating_map(db, floor_id)

    @staticmethod
    def list_seats(
        db: Session,
        floor_id: int | None = None,
        seat_status: str | None = None,
    ) -> list[SeatResponse]:
        return SeatService.list_seats(db, floor_id=floor_id, seat_status=seat_status)

    @staticmethod
    def get_seat(db: Session, seat_id: int) -> SeatResponse:
        return SeatService.get_seat(db, seat_id)

    @staticmethod
    def create_seat(db: Session, data: SeatCreate) -> SeatResponse:
        return SeatService.create_seat(db, data)

    @staticmethod
    def batch_create_seats(db: Session, data: SeatBatchCreate) -> list[SeatResponse]:
        return SeatService.batch_create_seats(db, data)

    @staticmethod
    def update_seat(db: Session, seat_id: int, data: SeatUpdate) -> SeatResponse:
        return SeatService.update_seat(db, seat_id, data)

    @staticmethod
    def delete_seat(db: Session, seat_id: int) -> dict[str, str]:
        SeatService.delete_seat(db, seat_id)
        return {"message": f"Seat {seat_id} successfully deleted"}

    @staticmethod
    def assign_seat(
        db: Session,
        seat_id: int,
        data: SeatAssignRequest,
        user_id: int,
    ) -> SeatResponse:
        return SeatService.assign_seat(
            db=db,
            seat_id=seat_id,
            employee_id=data.employee_id,
            user_id=user_id,
            notes=data.notes,
        )

    @staticmethod
    def release_seat(
        db: Session,
        seat_id: int,
        data: SeatReleaseRequest,
        user_id: int,
    ) -> SeatResponse:
        return SeatService.release_seat(
            db=db,
            seat_id=seat_id,
            user_id=user_id,
            notes=data.notes,
        )

    @staticmethod
    def relocate_seat(
        db: Session,
        data: SeatRelocateRequest,
        user_id: int,
    ) -> SeatResponse:
        return SeatService.relocate_seat(
            db=db,
            current_seat_id=data.current_seat_id,
            target_seat_id=data.target_seat_id,
            user_id=user_id,
            notes=data.notes,
        )

    @staticmethod
    def swap_seats(
        db: Session,
        data: SeatSwapRequest,
        user_id: int,
    ) -> list[SeatResponse]:
        return SeatService.swap_seats(
            db=db,
            seat_id=data.seat_id,
            target_employee_id=data.target_employee_id,
            user_id=user_id,
            notes=data.notes,
        )

    @staticmethod
    def get_seat_history(db: Session, seat_id: int) -> list[SeatHistoryResponse]:
        return SeatService.get_seat_history(db, seat_id)

    @staticmethod
    def get_employee_seat_history(
        db: Session, employee_id: int
    ) -> list[SeatHistoryResponse]:
        return SeatService.get_employee_seat_history(db, employee_id)
