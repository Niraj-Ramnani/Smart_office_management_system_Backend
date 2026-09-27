from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import (
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_MANAGER_APPROVED,
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_REJECTED,
    REQUEST_TYPE_NEW_SEAT,
    REQUEST_TYPE_RELOCATION,
    REQUEST_TYPE_SWAP,
    ROLE_ADMIN,
)
from app.models.employee import Employee
from app.models.permission_request import PermissionRequest
from app.models.user import User
from app.repositories.seat_repository import SeatRepository
from app.repositories.seat_request_repository import SeatRequestRepository
from app.schemas.seat_request import (
    SeatRequestCreate,
    SeatRequestExecute,
    SeatRequestResponse,
    SeatRequestReview,
)
from app.services.seat_service import SeatService


class SeatRequestService:
    @staticmethod
    def _to_response(req: PermissionRequest) -> SeatRequestResponse:
        emp_name = None
        emp_code = None
        emp_email = None
        dept = None
        if req.employee:
            emp_name = f"{req.employee.first_name} {req.employee.last_name}"
            emp_code = req.employee.employee_code
            emp_email = req.employee.email
            dept = req.employee.department

        approver_name = None
        if req.approver:
            approver_name = f"{req.approver.first_name} {req.approver.last_name}"

        executor_name = None
        if req.assignee:
            executor_name = f"{req.assignee.first_name} {req.assignee.last_name}"

        return SeatRequestResponse(
            id=req.id,
            employee_id=req.employee_id,
            employee_name=emp_name,
            employee_code=emp_code,
            employee_email=emp_email,
            department=dept,
            request_type=req.request_type,
            status=req.status,
            requested_for=req.requested_for,
            details=req.details,
            approved_by=req.approved_by,
            approver_name=approver_name,
            approved_at=req.approved_at,
            assigned_to=req.assigned_to,
            executor_name=executor_name,
            completed_at=req.completed_at,
            rejected_reason=req.rejected_reason,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )

    @staticmethod
    def create_request(
        db: Session,
        current_user: User,
        data: SeatRequestCreate,
    ) -> SeatRequestResponse:
        if not current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your user account is not linked to an employee profile",
            )

        valid_types = {REQUEST_TYPE_NEW_SEAT, REQUEST_TYPE_RELOCATION, REQUEST_TYPE_SWAP}
        if data.request_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request type '{data.request_type}'. Must be one of: {', '.join(sorted(valid_types))}",
            )

        details = {
            "preferred_seat_id": data.preferred_seat_id,
            "target_seat_id": data.target_seat_id,
            "target_employee_id": data.target_employee_id,
            "reason": data.reason,
        }

        current_seat = SeatRepository.get_by_employee_id(db, current_user.employee_id)

        if data.request_type == REQUEST_TYPE_NEW_SEAT:
            if current_seat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You already have an active seat ({current_seat.seat_number}). Use Relocation or Swap request instead.",
                )
        elif data.request_type == REQUEST_TYPE_RELOCATION:
            if not current_seat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You do not have an assigned seat to relocate from. Submit a New Seat request instead.",
                )
            details["current_seat_id"] = current_seat.id
            details["current_seat_number"] = current_seat.seat_number
        elif data.request_type == REQUEST_TYPE_SWAP:
            if not current_seat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You do not have an assigned seat to swap. Submit a New Seat request instead.",
                )
            if not data.target_employee_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target employee is required for a seat swap request",
                )
            if data.target_employee_id == current_user.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot request a seat swap with yourself",
                )
            target_seat = SeatRepository.get_by_employee_id(db, data.target_employee_id)
            if not target_seat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected target employee does not have an assigned seat to swap with",
                )
            details["current_seat_id"] = current_seat.id
            details["current_seat_number"] = current_seat.seat_number
            details["target_seat_id"] = target_seat.id
            details["target_seat_number"] = target_seat.seat_number

        req = SeatRequestRepository.create(
            db=db,
            employee_id=current_user.employee_id,
            request_type=data.request_type,
            details=details,
        )
        loaded_req = SeatRequestRepository.get_by_id(db, req.id)
        return SeatRequestService._to_response(loaded_req or req)

    @staticmethod
    def get_my_requests(db: Session, current_user: User) -> list[SeatRequestResponse]:
        if not current_user.employee_id:
            return []
        requests = SeatRequestRepository.get_by_employee(db, current_user.employee_id)
        return [SeatRequestService._to_response(r) for r in requests]

    @staticmethod
    def get_manager_requests(
        db: Session,
        current_user: User,
        status_filter: str | None = None,
    ) -> list[SeatRequestResponse]:
        if not current_user.employee_id:
            return []
        requests = SeatRequestRepository.get_by_manager(
            db,
            manager_employee_id=current_user.employee_id,
            status=status_filter,
        )
        return [SeatRequestService._to_response(r) for r in requests]

    @staticmethod
    def get_all_requests(
        db: Session,
        status_filter: str | None = None,
        request_type: str | None = None,
    ) -> list[SeatRequestResponse]:
        requests = SeatRequestRepository.get_all(db, status=status_filter, request_type=request_type)
        return [SeatRequestService._to_response(r) for r in requests]

    @staticmethod
    def get_approved_for_admin(db: Session) -> list[SeatRequestResponse]:
        requests = SeatRequestRepository.get_approved_for_admin(db)
        return [SeatRequestService._to_response(r) for r in requests]

    @staticmethod
    def review_request(
        db: Session,
        request_id: int,
        current_user: User,
        review_data: SeatRequestReview,
    ) -> SeatRequestResponse:
        req = SeatRequestRepository.get_by_id(db, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat request #{request_id} not found",
            )

        if req.status != REQUEST_STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot review request #{request_id} in status '{req.status}'. Must be '{REQUEST_STATUS_PENDING}'.",
            )

        user_role = current_user.role.name if current_user.role else ""
        is_admin = user_role == ROLE_ADMIN
        is_authorized_manager = (
            req.employee is not None
            and current_user.employee_id is not None
            and (
                req.employee.manager_id == current_user.employee_id
                or (
                    req.employee.team is not None
                    and req.employee.team.manager_id == current_user.employee_id
                )
            )
        )

        if not (is_admin or is_authorized_manager):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to review requests for this employee",
            )

        new_status = (
            REQUEST_STATUS_MANAGER_APPROVED
            if review_data.action == "APPROVE"
            else REQUEST_STATUS_REJECTED
        )

        updated = SeatRequestRepository.update(
            db=db,
            request=req,
            status=new_status,
            approved_by=current_user.employee_id,
            approved_at=datetime.now(timezone.utc),
            rejected_reason=review_data.rejected_reason if review_data.action == "REJECT" else None,
        )
        return SeatRequestService._to_response(updated)

    @staticmethod
    def execute_request(
        db: Session,
        request_id: int,
        current_user: User,
        exec_data: SeatRequestExecute,
    ) -> SeatRequestResponse:
        req = SeatRequestRepository.get_by_id(db, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat request #{request_id} not found",
            )

        if req.status != REQUEST_STATUS_MANAGER_APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot execute request #{request_id} with status '{req.status}'. It must be '{REQUEST_STATUS_MANAGER_APPROVED}'.",
            )

        details = req.details or {}

        if req.request_type == REQUEST_TYPE_NEW_SEAT:
            seat_id = exec_data.seat_id or details.get("preferred_seat_id")
            if not seat_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A target seat must be specified to execute this seat assignment",
                )
            SeatService.assign_seat(
                db=db,
                seat_id=int(seat_id),
                employee_id=req.employee_id,
                user_id=current_user.id,
                notes=exec_data.notes or f"Executed seat request #{req.id}",
            )

        elif req.request_type == REQUEST_TYPE_RELOCATION:
            from_seat = SeatRepository.get_by_employee_id(db, req.employee_id)
            if not from_seat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee currently has no active seat to relocate from",
                )
            to_seat_id = exec_data.seat_id or details.get("target_seat_id") or details.get("preferred_seat_id")
            if not to_seat_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A destination seat must be specified to execute this relocation",
                )
            SeatService.relocate_seat(
                db=db,
                from_seat_id=from_seat.id,
                to_seat_id=int(to_seat_id),
                user_id=current_user.id,
                notes=exec_data.notes or f"Executed relocation request #{req.id}",
            )

        elif req.request_type == REQUEST_TYPE_SWAP:
            target_emp_id = details.get("target_employee_id")
            if not target_emp_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target employee for swap not specified in request details",
                )
            seat_a = SeatRepository.get_by_employee_id(db, req.employee_id)
            seat_b = SeatRepository.get_by_employee_id(db, int(target_emp_id))
            if not seat_a or not seat_b:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Both employees must have an active seat assignment to execute swap",
                )
            SeatService.swap_seats(
                db=db,
                seat_a_id=seat_a.id,
                seat_b_id=seat_b.id,
                user_id=current_user.id,
                notes=exec_data.notes or f"Executed seat swap request #{req.id}",
            )

        updated = SeatRequestRepository.update(
            db=db,
            request=req,
            status=REQUEST_STATUS_COMPLETED,
            assigned_to=current_user.employee_id,
            completed_at=datetime.now(timezone.utc),
        )
        return SeatRequestService._to_response(updated)
