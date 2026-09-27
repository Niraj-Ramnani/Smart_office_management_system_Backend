from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.constants import (
    SEAT_ACTION_ASSIGN,
    SEAT_ACTION_RELEASE,
    SEAT_ACTION_RELOCATE,
    SEAT_ACTION_SWAP,
    SEAT_STATUS_OCCUPIED,
    SEAT_STATUS_VACANT,
)
from app.models.activity_log import ActivityLog
from app.models.employee import Employee
from app.models.floor import Floor
from app.models.seat import Seat
from app.models.seat_history import SeatHistory


class SeatRepository:
    @staticmethod
    def get_all(
        db: Session,
        floor_id: int | None = None,
        status: str | None = None,
    ) -> list[Seat]:
        query = (
            db.query(Seat)
            .options(
                joinedload(Seat.employee),
                joinedload(Seat.floor).joinedload(Floor.building),
            )
        )
        if floor_id is not None:
            query = query.filter(Seat.floor_id == floor_id)
        if status is not None:
            query = query.filter(Seat.status == status)
        return query.order_by(Seat.seat_number).all()

    @staticmethod
    def get_by_id(db: Session, seat_id: int) -> Seat | None:
        return (
            db.query(Seat)
            .options(
                joinedload(Seat.employee),
                joinedload(Seat.floor).joinedload(Floor.building),
            )
            .filter(Seat.id == seat_id)
            .first()
        )

    @staticmethod
    def get_by_employee_id(db: Session, employee_id: int) -> Seat | None:
        return (
            db.query(Seat)
            .options(
                joinedload(Seat.employee),
                joinedload(Seat.floor).joinedload(Floor.building),
            )
            .filter(Seat.employee_id == employee_id)
            .first()
        )

    @staticmethod
    def get_by_floor_and_number(
        db: Session, floor_id: int, seat_number: str
    ) -> Seat | None:
        return (
            db.query(Seat)
            .filter(
                Seat.floor_id == floor_id,
                func.lower(Seat.seat_number) == seat_number.strip().lower(),
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        floor_id: int,
        seat_number: str,
        seat_type: str = "Standard",
        x_position: float = 0.0,
        y_position: float = 0.0,
        status: str = "Vacant",
    ) -> Seat:
        seat = Seat(
            floor_id=floor_id,
            seat_number=seat_number.strip(),
            seat_type=seat_type.strip(),
            x_position=x_position,
            y_position=y_position,
            status=status,
            employee_id=None,
        )
        db.add(seat)
        db.commit()
        db.refresh(seat)
        return seat

    @staticmethod
    def update(db: Session, seat: Seat, **fields) -> Seat:
        for k, v in fields.items():
            setattr(seat, k, v)
        db.commit()
        db.refresh(seat)
        return seat

    @staticmethod
    def delete(db: Session, seat: Seat) -> None:
        db.delete(seat)
        db.commit()

    @staticmethod
    def assign_seat_transaction(
        db: Session,
        seat: Seat,
        employee: Employee,
        user_id: int,
        notes: str | None = None,
    ) -> Seat:
        seat.employee_id = employee.id
        seat.status = SEAT_STATUS_OCCUPIED

        history = SeatHistory(
            seat_id=seat.id,
            employee_id=employee.id,
            action=SEAT_ACTION_ASSIGN,
            start_date=datetime.now(),
            notes=notes or f"Assigned to {employee.first_name} {employee.last_name}",
        )
        db.add(history)

        activity = ActivityLog(
            user_id=user_id,
            action="ASSIGN_SEAT",
            entity_type="SEAT",
            entity_id=seat.id,
            description=f"Seat {seat.seat_number} assigned to {employee.first_name} {employee.last_name} ({employee.employee_code})",
        )
        db.add(activity)

        db.commit()
        db.refresh(seat)
        return seat

    @staticmethod
    def release_seat_transaction(
        db: Session,
        seat: Seat,
        user_id: int,
        notes: str | None = None,
    ) -> Seat:
        released_employee_id = seat.employee_id
        released_employee_name = (
            f"{seat.employee.first_name} {seat.employee.last_name}"
            if seat.employee
            else f"Employee ID {released_employee_id}"
        )

        active_history = (
            db.query(SeatHistory)
            .filter(
                SeatHistory.seat_id == seat.id,
                SeatHistory.employee_id == released_employee_id,
                SeatHistory.end_date.is_(None),
            )
            .first()
        )
        if active_history:
            active_history.end_date = datetime.now()

        release_history = SeatHistory(
            seat_id=seat.id,
            employee_id=released_employee_id,
            action=SEAT_ACTION_RELEASE,
            start_date=datetime.now(),
            end_date=datetime.now(),
            notes=notes or f"Seat released from {released_employee_name}",
        )
        db.add(release_history)

        seat.employee_id = None
        seat.status = SEAT_STATUS_VACANT

        activity = ActivityLog(
            user_id=user_id,
            action="RELEASE_SEAT",
            entity_type="SEAT",
            entity_id=seat.id,
            description=f"Seat {seat.seat_number} released from {released_employee_name}",
        )
        db.add(activity)

        db.commit()
        db.refresh(seat)
        return seat

    @staticmethod
    def relocate_seat_transaction(
        db: Session,
        current_seat: Seat,
        target_seat: Seat,
        employee: Employee,
        user_id: int,
        notes: str | None = None,
    ) -> Seat:
        active_history = (
            db.query(SeatHistory)
            .filter(
                SeatHistory.seat_id == current_seat.id,
                SeatHistory.employee_id == employee.id,
                SeatHistory.end_date.is_(None),
            )
            .first()
        )
        if active_history:
            active_history.end_date = datetime.now()

        current_seat.employee_id = None
        current_seat.status = SEAT_STATUS_VACANT

        target_seat.employee_id = employee.id
        target_seat.status = SEAT_STATUS_OCCUPIED

        history = SeatHistory(
            seat_id=target_seat.id,
            employee_id=employee.id,
            action=SEAT_ACTION_RELOCATE,
            start_date=datetime.now(),
            notes=notes or f"Relocated from Seat {current_seat.seat_number} to {target_seat.seat_number}",
        )
        db.add(history)

        activity = ActivityLog(
            user_id=user_id,
            action="RELOCATE_SEAT",
            entity_type="SEAT",
            entity_id=target_seat.id,
            description=f"Employee {employee.first_name} {employee.last_name} relocated from Seat {current_seat.seat_number} to {target_seat.seat_number}",
        )
        db.add(activity)

        db.commit()
        db.refresh(target_seat)
        return target_seat

    @staticmethod
    def swap_seats_transaction(
        db: Session,
        seat_a: Seat,
        seat_b: Seat,
        emp_a: Employee,
        emp_b: Employee,
        user_id: int,
        notes: str | None = None,
    ) -> tuple[Seat, Seat]:
        for seat_item, emp_item in [(seat_a, emp_a), (seat_b, emp_b)]:
            hist = (
                db.query(SeatHistory)
                .filter(
                    SeatHistory.seat_id == seat_item.id,
                    SeatHistory.employee_id == emp_item.id,
                    SeatHistory.end_date.is_(None),
                )
                .first()
            )
            if hist:
                hist.end_date = datetime.now()

        seat_a.employee_id = None
        db.flush()
        seat_b.employee_id = emp_a.id
        db.flush()
        seat_a.employee_id = emp_b.id
        db.flush()

        swap_note = notes or f"Swapped between {emp_a.first_name} {emp_a.last_name} and {emp_b.first_name} {emp_b.last_name}"

        hist_a = SeatHistory(
            seat_id=seat_a.id,
            employee_id=emp_b.id,
            action=SEAT_ACTION_SWAP,
            start_date=datetime.now(),
            notes=swap_note,
        )
        hist_b = SeatHistory(
            seat_id=seat_b.id,
            employee_id=emp_a.id,
            action=SEAT_ACTION_SWAP,
            start_date=datetime.now(),
            notes=swap_note,
        )
        db.add_all([hist_a, hist_b])

        activity = ActivityLog(
            user_id=user_id,
            action="SWAP_SEATS",
            entity_type="SEAT",
            entity_id=seat_a.id,
            description=f"Swapped seats: {seat_a.seat_number} ({emp_a.first_name}) <-> {seat_b.seat_number} ({emp_b.first_name})",
        )
        db.add(activity)

        db.commit()
        db.refresh(seat_a)
        db.refresh(seat_b)
        return seat_a, seat_b
