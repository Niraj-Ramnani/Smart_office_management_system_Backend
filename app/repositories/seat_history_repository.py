from sqlalchemy.orm import Session, joinedload

from app.models.seat_history import SeatHistory


class SeatHistoryRepository:
    @staticmethod
    def get_by_seat_id(db: Session, seat_id: int) -> list[SeatHistory]:
        return (
            db.query(SeatHistory)
            .options(
                joinedload(SeatHistory.employee),
                joinedload(SeatHistory.seat),
            )
            .filter(SeatHistory.seat_id == seat_id)
            .order_by(SeatHistory.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_employee_id(db: Session, employee_id: int) -> list[SeatHistory]:
        return (
            db.query(SeatHistory)
            .options(
                joinedload(SeatHistory.employee),
                joinedload(SeatHistory.seat),
            )
            .filter(SeatHistory.employee_id == employee_id)
            .order_by(SeatHistory.created_at.desc())
            .all()
        )
