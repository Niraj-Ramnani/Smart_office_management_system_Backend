from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import (
    EMPLOYEE_STATUS_ACTIVE,
    SEAT_STATUS_BLOCKED,
    SEAT_STATUS_OCCUPIED,
    SEAT_STATUS_VACANT,
)
from app.models.building import Building
from app.models.employee import Employee
from app.models.floor import Floor
from app.models.seat import Seat
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.floor_repository import FloorRepository
from app.repositories.seat_history_repository import SeatHistoryRepository
from app.repositories.seat_repository import SeatRepository
from app.schemas.seat import (
    BuildingSeatingSummary,
    FloorSeatingMapResponse,
    FloorSummaryItem,
    RoleDistributionItem,
    SeatBatchCreate,
    SeatCreate,
    SeatHistoryResponse,
    SeatResponse,
    SeatUpdate,
    SeatingOverviewResponse,
)

class SeatService:
    @staticmethod
    def _to_response(seat: Seat) -> SeatResponse:
        emp_name = None
        emp_code = None
        emp_email = None
        if seat.employee:
            emp_name = f"{seat.employee.first_name} {seat.employee.last_name}"
            emp_code = seat.employee.employee_code
            emp_email = seat.employee.email

        b_id = None
        b_name = None
        f_name = None
        f_num = None
        if seat.floor:
            f_name = seat.floor.name
            f_num = seat.floor.floor_number
            if seat.floor.building:
                b_id = seat.floor.building.id
                b_name = seat.floor.building.name

        return SeatResponse(
            id=seat.id,
            floor_id=seat.floor_id,
            seat_number=seat.seat_number,
            seat_type=seat.seat_type,
            status=seat.status,
            x_position=float(seat.x_position),
            y_position=float(seat.y_position),
            employee_id=seat.employee_id,
            employee_name=emp_name,
            employee_code=emp_code,
            employee_email=emp_email,
            building_id=b_id,
            building_name=b_name,
            floor_name=f_name,
            floor_number=f_num,
            created_at=seat.created_at,
            updated_at=seat.updated_at,
        )

    @staticmethod
    def get_seating_overview(db: Session) -> SeatingOverviewResponse:
        buildings = db.query(Building).all()
        building_summaries: list[BuildingSeatingSummary] = []
        overall_total = 0
        overall_occupied = 0
        overall_vacant = 0
        overall_blocked = 0

        for b in buildings:
            floors = (
                db.query(Floor)
                .filter(Floor.building_id == b.id)
                .order_by(Floor.floor_number)
                .all()
            )
            b_total = 0
            b_occupied = 0
            b_vacant = 0
            floor_summaries: list[FloorSummaryItem] = []

            for f in floors:
                f_seats = db.query(Seat).filter(Seat.floor_id == f.id).all()
                f_total = len(f_seats)
                f_occ = sum(1 for s in f_seats if s.status == SEAT_STATUS_OCCUPIED)
                f_vac = sum(1 for s in f_seats if s.status == SEAT_STATUS_VACANT)
                f_blk = sum(1 for s in f_seats if s.status == SEAT_STATUS_BLOCKED)

                b_total += f_total
                b_occupied += f_occ
                b_vacant += f_vac
                overall_blocked += f_blk

                floor_summaries.append(
                    FloorSummaryItem(
                        floor_id=f.id,
                        floor_name=f.name,
                        floor_number=f.floor_number,
                        total_seats=f_total,
                        occupied_seats=f_occ,
                        vacant_seats=f_vac,
                    )
                )

            overall_total += b_total
            overall_occupied += b_occupied
            overall_vacant += b_vacant

            building_summaries.append(
                BuildingSeatingSummary(
                    building_id=b.id,
                    building_name=b.name,
                    total_seats=b_total,
                    occupied_seats=b_occupied,
                    vacant_seats=b_vacant,
                    floors=floor_summaries,
                )
            )

        occupied_seats_query = (
            db.query(Employee.designation, func.count(Seat.id))
            .join(Seat, Seat.employee_id == Employee.id)
            .filter(Seat.status == SEAT_STATUS_OCCUPIED)
            .group_by(Employee.designation)
            .all()
        )
        total_counted = sum(count for _, count in occupied_seats_query)
        role_items: list[RoleDistributionItem] = []
        for desig, count in occupied_seats_query:
            pct = f"{round((count / total_counted) * 100)}%" if total_counted > 0 else "0%"
            role_items.append(
                RoleDistributionItem(
                    role_name=desig or "General Staff",
                    count=count,
                    percent=pct,
                )
            )

        return SeatingOverviewResponse(
            total_seats=overall_total,
            total_occupied=overall_occupied,
            total_vacant=overall_vacant,
            total_blocked=overall_blocked,
            buildings=building_summaries,
            role_distribution=role_items,
        )

    @staticmethod
    def get_floor_seating_map(db: Session, floor_id: int) -> FloorSeatingMapResponse:
        floor = FloorRepository.get_by_id(db, floor_id)
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID {floor_id} not found",
            )

        seats = SeatRepository.get_all(db, floor_id=floor_id)
        total_seats = len(seats)
        occupied_seats = sum(1 for s in seats if s.status == SEAT_STATUS_OCCUPIED)
        vacant_seats = sum(1 for s in seats if s.status == SEAT_STATUS_VACANT)
        blocked_seats = sum(1 for s in seats if s.status == SEAT_STATUS_BLOCKED)

        return FloorSeatingMapResponse(
            floor_id=floor.id,
            floor_name=floor.name,
            floor_number=floor.floor_number,
            building_id=floor.building.id if floor.building else 0,
            building_name=floor.building.name if floor.building else "Unknown",
            map_width=floor.map_width,
            map_height=floor.map_height,
            total_seats=total_seats,
            occupied_seats=occupied_seats,
            vacant_seats=vacant_seats,
            blocked_seats=blocked_seats,
            seats=[SeatService._to_response(s) for s in seats],
        )

    @staticmethod
    def list_seats(
        db: Session,
        floor_id: int | None = None,
        seat_status: str | None = None,
    ) -> list[SeatResponse]:
        seats = SeatRepository.get_all(db, floor_id=floor_id, status=seat_status)
        return [SeatService._to_response(s) for s in seats]

    @staticmethod
    def get_seat(db: Session, seat_id: int) -> SeatResponse:
        seat = SeatRepository.get_by_id(db, seat_id)
        if not seat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat with ID {seat_id} not found",
            )
        return SeatService._to_response(seat)

    @staticmethod
    def create_seat(db: Session, data: SeatCreate) -> SeatResponse:
        floor = FloorRepository.get_by_id(db, data.floor_id)
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Floor with ID {data.floor_id} not found",
            )

        existing = SeatRepository.get_by_floor_and_number(
            db, data.floor_id, data.seat_number
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seat number '{data.seat_number}' already exists on floor '{floor.name}'",
            )

        seat = SeatRepository.create(
            db=db,
            floor_id=data.floor_id,
            seat_number=data.seat_number,
            seat_type=data.seat_type,
            x_position=data.x_position,
            y_position=data.y_position,
            status=data.status,
        )
        return SeatService._to_response(seat)

    @staticmethod
    def batch_create_seats(db: Session, data: SeatBatchCreate) -> list[SeatResponse]:
        floor = FloorRepository.get_by_id(db, data.floor_id)
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Floor with ID {data.floor_id} not found",
            )

        existing_seats = SeatRepository.get_all(db, floor_id=data.floor_id)
        existing_numbers = {s.seat_number.upper() for s in existing_seats}

        raw_prefix = data.prefix
        prefix = raw_prefix.lstrip() if raw_prefix.endswith(" ") else raw_prefix.strip()
        start_num = data.start_number

        if start_num is None:
            max_num = 0
            for s in existing_seats:
                if s.seat_number.upper().startswith(prefix.upper()):
                    suffix = s.seat_number[len(prefix):]
                    try:
                        num = int(suffix)
                        if num > max_num:
                            max_num = num
                    except ValueError:
                        pass
            start_num = max_num + 1

        created_seats: list[Seat] = []
        for i in range(data.count):
            num = start_num + i
            seat_num = f"{prefix}{num:02d}"
            if seat_num.upper() in existing_numbers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Seat number '{seat_num}' already exists on floor '{floor.name}'",
                )

            x_pos = 100.0 + (len(existing_seats) + i) * 60.0
            y_pos = 150.0

            seat = SeatRepository.create(
                db=db,
                floor_id=data.floor_id,
                seat_number=seat_num,
                seat_type=data.seat_type,
                x_position=x_pos,
                y_position=y_pos,
                status=SEAT_STATUS_VACANT,
            )
            existing_numbers.add(seat_num.upper())
            created_seats.append(seat)

        return [SeatService._to_response(s) for s in created_seats]

    @staticmethod
    def update_seat(db: Session, seat_id: int, data: SeatUpdate) -> SeatResponse:
        seat = SeatRepository.get_by_id(db, seat_id)
        if not seat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat with ID {seat_id} not found",
            )

        fields: dict = {}
        if data.seat_number is not None:
            clean_num = data.seat_number.strip()
            if clean_num.lower() != seat.seat_number.lower():
                existing = SeatRepository.get_by_floor_and_number(
                    db, seat.floor_id, clean_num
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Seat number '{clean_num}' already exists on this floor",
                    )
            fields["seat_number"] = clean_num

        if data.seat_type is not None:
            fields["seat_type"] = data.seat_type.strip()
        if data.x_position is not None:
            fields["x_position"] = data.x_position
        if data.y_position is not None:
            fields["y_position"] = data.y_position
        if data.status is not None:
            if data.status == SEAT_STATUS_OCCUPIED and seat.employee_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot set status to Occupied without an assigned employee. Use the assign endpoint.",
                )
            fields["status"] = data.status.strip()

        updated = SeatRepository.update(db, seat, **fields)
        return SeatService._to_response(updated)

    @staticmethod
    def delete_seat(db: Session, seat_id: int) -> None:
        seat = SeatRepository.get_by_id(db, seat_id)
        if not seat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat with ID {seat_id} not found",
            )
        if seat.status == SEAT_STATUS_OCCUPIED or seat.employee_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete an occupied seat. Release the seat assignment first.",
            )
        SeatRepository.delete(db, seat)

    @staticmethod
    def assign_seat(
        db: Session,
        seat_id: int,
        employee_id: int,
        user_id: int,
        notes: str | None = None,
    ) -> SeatResponse:
        seat = SeatRepository.get_by_id(db, seat_id)
        if not seat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat with ID {seat_id} not found",
            )

        if seat.status == SEAT_STATUS_BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seat '{seat.seat_number}' is blocked and cannot be assigned",
            )

        if seat.employee_id is not None or seat.status == SEAT_STATUS_OCCUPIED:
            occupant = seat.employee
            occupant_name = (
                f"{occupant.first_name} {occupant.last_name}"
                if occupant
                else f"Employee ID {seat.employee_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seat '{seat.seat_number}' is already occupied by {occupant_name}. Release it first or perform a relocation/swap.",
            )

        employee = EmployeeRepository.get_by_id(db, employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with ID {employee_id} not found",
            )

        if employee.employee_status != EMPLOYEE_STATUS_ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot assign seat to inactive employee '{employee.first_name} {employee.last_name}'",
            )

        current_assignment = SeatRepository.get_by_employee_id(db, employee_id)
        if current_assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee '{employee.first_name} {employee.last_name}' already has an active seat assignment (Seat '{current_assignment.seat_number}'). Use the relocation action instead.",
            )

        assigned_seat = SeatRepository.assign_seat_transaction(
            db=db,
            seat=seat,
            employee=employee,
            user_id=user_id,
            notes=notes,
        )
        return SeatService._to_response(assigned_seat)

    @staticmethod
    def release_seat(
        db: Session,
        seat_id: int,
        user_id: int,
        notes: str | None = None,
    ) -> SeatResponse:
        seat = SeatRepository.get_by_id(db, seat_id)
        if not seat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat with ID {seat_id} not found",
            )

        if seat.employee_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seat '{seat.seat_number}' is already vacant",
            )

        released_seat = SeatRepository.release_seat_transaction(
            db=db,
            seat=seat,
            user_id=user_id,
            notes=notes,
        )
        return SeatService._to_response(released_seat)

    @staticmethod
    def relocate_seat(
        db: Session,
        current_seat_id: int,
        target_seat_id: int,
        user_id: int,
        notes: str | None = None,
    ) -> SeatResponse:
        if current_seat_id == target_seat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and target seat cannot be the same",
            )

        current_seat = SeatRepository.get_by_id(db, current_seat_id)
        if not current_seat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source seat with ID {current_seat_id} not found",
            )

        if current_seat.employee_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source seat '{current_seat.seat_number}' has no assigned employee to relocate",
            )

        target_seat = SeatRepository.get_by_id(db, target_seat_id)
        if not target_seat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target seat with ID {target_seat_id} not found",
            )

        if target_seat.status == SEAT_STATUS_BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target seat '{target_seat.seat_number}' is blocked",
            )

        if target_seat.employee_id is not None or target_seat.status == SEAT_STATUS_OCCUPIED:
            occupant = target_seat.employee
            occupant_name = (
                f"{occupant.first_name} {occupant.last_name}"
                if occupant
                else f"Employee ID {target_seat.employee_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target seat '{target_seat.seat_number}' is already occupied by {occupant_name}. Use the swap operation instead.",
            )

        employee = current_seat.employee
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned employee record not found",
            )

        relocated_seat = SeatRepository.relocate_seat_transaction(
            db=db,
            current_seat=current_seat,
            target_seat=target_seat,
            employee=employee,
            user_id=user_id,
            notes=notes,
        )
        return SeatService._to_response(relocated_seat)

    @staticmethod
    def swap_seats(
        db: Session,
        seat_id: int,
        target_employee_id: int,
        user_id: int,
        notes: str | None = None,
    ) -> list[SeatResponse]:
        seat_a = SeatRepository.get_by_id(db, seat_id)
        if not seat_a:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat with ID {seat_id} not found",
            )

        if seat_a.employee_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seat '{seat_a.seat_number}' is vacant and cannot be swapped",
            )

        emp_a = seat_a.employee
        if not emp_a:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee assigned to seat A not found",
            )

        if emp_a.id == target_employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot swap seat with the same employee",
            )

        emp_b = EmployeeRepository.get_by_id(db, target_employee_id)
        if not emp_b:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target employee with ID {target_employee_id} not found",
            )

        if emp_b.employee_status != EMPLOYEE_STATUS_ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target employee '{emp_b.first_name} {emp_b.last_name}' is inactive",
            )

        seat_b = SeatRepository.get_by_employee_id(db, target_employee_id)
        if not seat_b:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target employee '{emp_b.first_name} {emp_b.last_name}' does not have an assigned seat to swap with. Use relocation instead.",
            )

        if seat_a.id == seat_b.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both employees are linked to the same seat",
            )

        res_a, res_b = SeatRepository.swap_seats_transaction(
            db=db,
            seat_a=seat_a,
            seat_b=seat_b,
            emp_a=emp_a,
            emp_b=emp_b,
            user_id=user_id,
            notes=notes,
        )
        return [SeatService._to_response(res_a), SeatService._to_response(res_b)]

    @staticmethod
    def get_seat_history(db: Session, seat_id: int) -> list[SeatHistoryResponse]:
        seat = SeatRepository.get_by_id(db, seat_id)
        if not seat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat with ID {seat_id} not found",
            )

        histories = SeatHistoryRepository.get_by_seat_id(db, seat_id)
        result: list[SeatHistoryResponse] = []
        for h in histories:
            emp_name = f"{h.employee.first_name} {h.employee.last_name}" if h.employee else "Unknown"
            emp_code = h.employee.employee_code if h.employee else "Unknown"
            result.append(
                SeatHistoryResponse(
                    id=h.id,
                    seat_id=h.seat_id,
                    seat_number=seat.seat_number,
                    employee_id=h.employee_id,
                    employee_name=emp_name,
                    employee_code=emp_code,
                    action=h.action,
                    start_date=h.start_date,
                    end_date=h.end_date,
                    notes=h.notes,
                    created_at=h.created_at,
                )
            )
        return result
