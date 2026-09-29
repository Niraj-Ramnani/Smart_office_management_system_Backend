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
from app.services.notification_service import ws_manager
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
        res = SeatService.create_seat(db, data)
        ws_manager.broadcast_entity_change("Seat", "created", ["Seat", "Floor", "Building"])
        return res

    @staticmethod
    def batch_create_seats(db: Session, data: SeatBatchCreate) -> list[SeatResponse]:
        res = SeatService.batch_create_seats(db, data)
        ws_manager.broadcast_entity_change("Seat", "batch_created", ["Seat", "Floor", "Building"])
        return res

    @staticmethod
    def update_seat(db: Session, seat_id: int, data: SeatUpdate) -> SeatResponse:
        res = SeatService.update_seat(db, seat_id, data)
        ws_manager.broadcast_entity_change("Seat", "updated", ["Seat", "Floor", "Building", "Employee"])
        return res

    @staticmethod
    def delete_seat(db: Session, seat_id: int) -> dict[str, str]:
        SeatService.delete_seat(db, seat_id)
        ws_manager.broadcast_entity_change("Seat", "deleted", ["Seat", "Floor", "Building"])
        return {"message": f"Seat {seat_id} successfully deleted"}

    @staticmethod
    def assign_seat(
        db: Session,
        seat_id: int,
        data: SeatAssignRequest,
        user_id: int,
    ) -> SeatResponse:
        res = SeatService.assign_seat(
            db=db,
            seat_id=seat_id,
            employee_id=data.employee_id,
            user_id=user_id,
            notes=data.notes,
        )
        ws_manager.broadcast_entity_change("Seat", "assigned", ["Seat", "Employee", "SeatRequest", "Notification"])
        return res

    @staticmethod
    def release_seat(
        db: Session,
        seat_id: int,
        data: SeatReleaseRequest,
        user_id: int,
    ) -> SeatResponse:
        res = SeatService.release_seat(
            db=db,
            seat_id=seat_id,
            user_id=user_id,
            notes=data.notes,
        )
        ws_manager.broadcast_entity_change("Seat", "released", ["Seat", "Employee", "SeatRequest", "Notification"])
        return res

    @staticmethod
    def relocate_seat(
        db: Session,
        data: SeatRelocateRequest,
        user_id: int,
    ) -> SeatResponse:
        res = SeatService.relocate_seat(
            db=db,
            current_seat_id=data.current_seat_id,
            target_seat_id=data.target_seat_id,
            user_id=user_id,
            notes=data.notes,
        )
        ws_manager.broadcast_entity_change("Seat", "relocated", ["Seat", "Employee", "SeatRequest", "Notification"])
        return res

    @staticmethod
    def swap_seats(
        db: Session,
        data: SeatSwapRequest,
        user_id: int,
    ) -> list[SeatResponse]:
        res = SeatService.swap_seats(
            db=db,
            seat_id=data.seat_id,
            target_employee_id=data.target_employee_id,
            user_id=user_id,
            notes=data.notes,
        )
        ws_manager.broadcast_entity_change("Seat", "swapped", ["Seat", "Employee", "SeatRequest", "Notification"])
        return res

    @staticmethod
    def get_seat_history(db: Session, seat_id: int) -> list[SeatHistoryResponse]:
        return SeatService.get_seat_history(db, seat_id)

    @staticmethod
    def get_employee_seat_history(
        db: Session, employee_id: int
    ) -> list[SeatHistoryResponse]:
        return SeatService.get_employee_seat_history(db, employee_id)
