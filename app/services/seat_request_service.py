from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import (
    ASSET_TYPES,
    NOTIFICATION_TYPE_APPROVAL,
    NOTIFICATION_TYPE_EXECUTION,
    NOTIFICATION_TYPE_REQUEST,
    NOTIFICATION_TYPE_SWAP_CONSENT,
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_MANAGER_APPROVED,
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_PENDING_CONSENT,
    REQUEST_STATUS_REJECTED,
    REQUEST_TYPE_ASSET_MAINTENANCE,
    REQUEST_TYPE_ASSET_NEW,
    REQUEST_TYPE_ASSET_REPLACEMENT,
    REQUEST_TYPE_NEW_SEAT,
    REQUEST_TYPE_RELOCATION,
    REQUEST_TYPE_SWAP,
    ROLE_ADMIN,
    ROLE_MANAGER,
    SEAT_STATUS_OCCUPIED,
)
from app.models.employee import Employee
from app.models.permission_request import PermissionRequest
from app.models.seat import Seat
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.seat_repository import SeatRepository
from app.repositories.seat_request_repository import SeatRequestRepository
from app.schemas.asset import AssetAllocate, AssetMaintenance, AssetReplace
from app.schemas.seat_request import (
    SeatRequestCreate,
    SeatRequestExecute,
    SeatRequestResponse,
    SeatRequestReview,
    SwapConsentAction,
)
from app.services.asset_service import AssetService
from app.services.notification_service import NotificationService
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

        valid_types = {
            REQUEST_TYPE_NEW_SEAT,
            REQUEST_TYPE_RELOCATION,
            REQUEST_TYPE_SWAP,
            REQUEST_TYPE_ASSET_NEW,
            REQUEST_TYPE_ASSET_MAINTENANCE,
            REQUEST_TYPE_ASSET_REPLACEMENT,
        }
        if data.request_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request type '{data.request_type}'. Must be one of: {', '.join(sorted(valid_types))}",
            )

        user_role = current_user.role.name if current_user.role else ""
        is_manager_or_admin = user_role in (ROLE_MANAGER, ROLE_ADMIN)

        target_emp_id = current_user.employee_id
        is_manager_initiated = False

        if data.employee_id and data.employee_id != current_user.employee_id:
            if not is_manager_or_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only managers or admins can create requests on behalf of other employees",
                )
            target_emp = EmployeeRepository.get_by_id(db, data.employee_id)
            if not target_emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee #{data.employee_id} not found",
                )
            if user_role == ROLE_MANAGER and target_emp.manager_id != current_user.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Managers can only create requests for employees they directly manage",
                )
            target_emp_id = data.employee_id
            is_manager_initiated = True

        employee = EmployeeRepository.get_by_id(db, target_emp_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found",
            )

        details = {
            "reason": data.reason,
            "manager_initiated": is_manager_initiated,
            "created_by_user_id": current_user.id,
            "created_by_employee_id": current_user.employee_id,
        }

        initial_status = REQUEST_STATUS_PENDING

        if data.request_type in (
            REQUEST_TYPE_ASSET_NEW,
            REQUEST_TYPE_ASSET_MAINTENANCE,
            REQUEST_TYPE_ASSET_REPLACEMENT,
        ):
            if not data.asset_type or data.asset_type not in ASSET_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Valid asset type is required ({', '.join(ASSET_TYPES)})",
                )
            details["asset_type"] = data.asset_type
            details["current_asset_id"] = data.current_asset_id
            if data.current_asset_id:
                curr_asset = AssetRepository.get_by_id(db, data.current_asset_id)
                if curr_asset:
                    details["current_asset_code"] = curr_asset.asset_code
                    details["current_asset_name"] = curr_asset.name

            if employee.manager_id:
                NotificationService.notify_employee(
                    db=db,
                    employee_id=employee.manager_id,
                    title="New Asset Request",
                    message=f"{employee.first_name} {employee.last_name} submitted a {data.asset_type} ({data.request_type}) request awaiting your approval.",
                    type=NOTIFICATION_TYPE_REQUEST,
                )

        else:
            current_seat = SeatRepository.get_by_employee_id(db, target_emp_id)

            if data.request_type == REQUEST_TYPE_NEW_SEAT:
                if current_seat:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Employee already has an active seat ({current_seat.seat_number}). Use Relocation or Swap request instead.",
                    )
                details["preferred_seat_id"] = data.preferred_seat_id

            elif data.request_type == REQUEST_TYPE_RELOCATION:
                if not current_seat:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Employee does not have an assigned seat to relocate from. Submit a New Seat request instead.",
                    )
                details["current_seat_id"] = current_seat.id
                details["current_seat_number"] = current_seat.seat_number

                dest_seat_id = data.target_seat_id or data.preferred_seat_id
                if dest_seat_id:
                    details["target_seat_id"] = dest_seat_id
                    dest_seat = SeatRepository.get_by_id(db, dest_seat_id)
                    if dest_seat:
                        details["target_seat_number"] = dest_seat.seat_number
                        if dest_seat.status == SEAT_STATUS_OCCUPIED and dest_seat.employee_id:
                            data.target_employee_id = dest_seat.employee_id
                            data.request_type = REQUEST_TYPE_SWAP

            if data.request_type == REQUEST_TYPE_SWAP:
                if not current_seat:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Employee must have an assigned seat to request a swap.",
                    )
                if not data.target_employee_id and data.target_seat_id:
                    target_seat_obj = SeatRepository.get_by_id(db, data.target_seat_id)
                    if target_seat_obj and target_seat_obj.employee_id:
                        data.target_employee_id = target_seat_obj.employee_id

                if not data.target_employee_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Target employee or occupied target seat is required for a seat swap request",
                    )
                if data.target_employee_id == target_emp_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot request a seat swap with the same employee",
                    )

                target_seat = SeatRepository.get_by_employee_id(db, data.target_employee_id)
                if not target_seat:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Selected target employee does not currently have an assigned seat to swap with",
                    )

                target_emp_record = EmployeeRepository.get_by_id(db, data.target_employee_id)
                details["current_seat_id"] = current_seat.id
                details["current_seat_number"] = current_seat.seat_number
                details["target_seat_id"] = target_seat.id
                details["target_seat_number"] = target_seat.seat_number
                details["target_employee_id"] = data.target_employee_id
                details["target_employee_name"] = (
                    f"{target_emp_record.first_name} {target_emp_record.last_name}"
                    if target_emp_record
                    else None
                )
                details["swap_status"] = "PENDING_CONSENT"
                initial_status = REQUEST_STATUS_PENDING_CONSENT

                NotificationService.notify_employee(
                    db=db,
                    employee_id=data.target_employee_id,
                    title="Seat Swap Requested",
                    message=f"{employee.first_name} {employee.last_name} has requested to swap desks with you (Desk {target_seat.seat_number}). Please review and accept or decline.",
                    type=NOTIFICATION_TYPE_SWAP_CONSENT,
                )

            elif is_manager_initiated:
                initial_status = REQUEST_STATUS_MANAGER_APPROVED
                details["approved_by_manager_direct"] = True
                NotificationService.notify_admins(
                    db=db,
                    title="Approved Seat Change Queued",
                    message=f"Manager initiated seat change for {employee.first_name} {employee.last_name} ready for Admin/Ops execution.",
                    type=NOTIFICATION_TYPE_APPROVAL,
                )

        req = SeatRequestRepository.create(
            db=db,
            employee_id=target_emp_id,
            request_type=data.request_type,
            details=details,
        )

        if initial_status != REQUEST_STATUS_PENDING:
            req.status = initial_status
            if initial_status == REQUEST_STATUS_MANAGER_APPROVED:
                req.approved_by = current_user.employee_id
                req.approved_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(req)

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
    def respond_swap_consent(
        db: Session,
        request_id: int,
        current_user: User,
        action_data: SwapConsentAction,
    ) -> SeatRequestResponse:
        req = SeatRequestRepository.get_by_id(db, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat swap request #{request_id} not found",
            )

        if req.status != REQUEST_STATUS_PENDING_CONSENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request #{request_id} is not awaiting swap consent (current status: '{req.status}')",
            )

        details = dict(req.details or {})
        target_emp_id = details.get("target_employee_id")

        if current_user.employee_id != target_emp_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the target seat occupant can accept or decline this swap request",
            )

        emp_a = EmployeeRepository.get_by_id(db, req.employee_id)
        emp_b = EmployeeRepository.get_by_id(db, target_emp_id)

        if action_data.action == "REJECT":
            details["swap_status"] = "DECLINED_BY_TARGET"
            req.status = REQUEST_STATUS_REJECTED
            req.rejected_reason = "Seat swap was declined by the current seat occupant."
            req.details = details
            db.commit()
            db.refresh(req)

            if emp_a:
                NotificationService.notify_employee(
                    db=db,
                    employee_id=emp_a.id,
                    title="Seat Swap Declined",
                    message=f"{emp_b.first_name if emp_b else 'The occupant'} declined your seat swap request.",
                    type=NOTIFICATION_TYPE_APPROVAL,
                )
            return SeatRequestService._to_response(req)

        details["swap_status"] = "CONSENT_ACCEPTED"
        details["consent_accepted_at"] = datetime.now(timezone.utc).isoformat()

        mgr_a = emp_a.manager_id if emp_a else None
        mgr_b = emp_b.manager_id if emp_b else None

        if mgr_a == mgr_b:
            req.status = REQUEST_STATUS_PENDING
            details["requires_dual_manager"] = False
            req.details = details
            db.commit()
            db.refresh(req)

            if mgr_a:
                NotificationService.notify_employee(
                    db=db,
                    employee_id=mgr_a,
                    title="Seat Swap Approval Required",
                    message=f"Seat swap between {emp_a.first_name} and {emp_b.first_name} consented by both employees and awaits your approval.",
                    type=NOTIFICATION_TYPE_REQUEST,
                )
        else:
            req.status = REQUEST_STATUS_PENDING
            details["requires_dual_manager"] = True
            details["manager_a_id"] = mgr_a
            details["manager_b_id"] = mgr_b
            details["manager_a_approved"] = False
            details["manager_b_approved"] = False
            req.details = details
            db.commit()
            db.refresh(req)

            if mgr_a:
                NotificationService.notify_employee(
                    db=db,
                    employee_id=mgr_a,
                    title="Seat Swap Approval Required",
                    message=f"Seat swap requested by your team member {emp_a.first_name} with {emp_b.first_name} awaits your approval.",
                    type=NOTIFICATION_TYPE_REQUEST,
                )
            if mgr_b:
                NotificationService.notify_employee(
                    db=db,
                    employee_id=mgr_b,
                    title="Seat Swap Approval Required",
                    message=f"Seat swap involving your team member {emp_b.first_name} with {emp_a.first_name} awaits your approval.",
                    type=NOTIFICATION_TYPE_REQUEST,
                )

        if emp_a:
            NotificationService.notify_employee(
                db=db,
                employee_id=emp_a.id,
                title="Seat Swap Consented",
                message=f"{emp_b.first_name if emp_b else 'The occupant'} accepted your swap request! It is now pending manager approval.",
                type=NOTIFICATION_TYPE_APPROVAL,
            )

        return SeatRequestService._to_response(req)

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

        details = dict(req.details or {})
        requires_dual = details.get("requires_dual_manager", False)

        is_mgr_a = False
        is_mgr_b = False

        if req.employee and current_user.employee_id:
            if req.employee.manager_id == current_user.employee_id or (
                req.employee.team and req.employee.team.manager_id == current_user.employee_id
            ):
                is_mgr_a = True

        if requires_dual and current_user.employee_id:
            target_emp_id = details.get("target_employee_id")
            if target_emp_id:
                target_emp = EmployeeRepository.get_by_id(db, target_emp_id)
                if target_emp and (
                    target_emp.manager_id == current_user.employee_id
                    or (target_emp.team and target_emp.team.manager_id == current_user.employee_id)
                ):
                    is_mgr_b = True

        if not (is_admin or is_mgr_a or is_mgr_b):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to review requests for this employee",
            )

        if review_data.action == "REJECT":
            req.status = REQUEST_STATUS_REJECTED
            req.approved_by = current_user.employee_id
            req.approved_at = datetime.now(timezone.utc)
            req.rejected_reason = review_data.rejected_reason or "Request rejected by manager"
            db.commit()
            db.refresh(req)

            NotificationService.notify_employee(
                db=db,
                employee_id=req.employee_id,
                title="Request Rejected",
                message=f"Your {req.request_type} request #{req.id} was rejected. Reason: {req.rejected_reason}",
                type=NOTIFICATION_TYPE_APPROVAL,
            )

            target_emp_id = details.get("target_employee_id")
            if target_emp_id and req.request_type == REQUEST_TYPE_SWAP:
                NotificationService.notify_employee(
                    db=db,
                    employee_id=target_emp_id,
                    title="Seat Swap Request Rejected",
                    message=f"Seat swap request #{req.id} was rejected by management.",
                    type=NOTIFICATION_TYPE_APPROVAL,
                )

            return SeatRequestService._to_response(req)

        if requires_dual:
            if is_mgr_a or is_admin:
                details["manager_a_approved"] = True
            if is_mgr_b or is_admin:
                details["manager_b_approved"] = True

            both_approved = details.get("manager_a_approved") and details.get("manager_b_approved")
            if both_approved or is_admin:
                req.status = REQUEST_STATUS_MANAGER_APPROVED
                req.approved_by = current_user.employee_id
                req.approved_at = datetime.now(timezone.utc)
                req.details = details
                db.commit()
                db.refresh(req)

                NotificationService.notify_employee(
                    db=db,
                    employee_id=req.employee_id,
                    title="Seat Swap Approved by Both Managers",
                    message=f"Seat swap request #{req.id} has been fully approved and queued for Admin/Ops execution.",
                    type=NOTIFICATION_TYPE_APPROVAL,
                )
                target_emp_id = details.get("target_employee_id")
                if target_emp_id:
                    NotificationService.notify_employee(
                        db=db,
                        employee_id=target_emp_id,
                        title="Seat Swap Approved by Both Managers",
                        message=f"Seat swap request #{req.id} has been fully approved and queued for Admin/Ops execution.",
                        type=NOTIFICATION_TYPE_APPROVAL,
                    )
                NotificationService.notify_admins(
                    db=db,
                    title="Approved Seat Swap Queued",
                    message=f"Seat swap request #{req.id} between #{req.employee_id} and #{target_emp_id} ready for execution.",
                    type=NOTIFICATION_TYPE_APPROVAL,
                )
            else:
                req.details = details
                db.commit()
                db.refresh(req)
                NotificationService.notify_employee(
                    db=db,
                    employee_id=req.employee_id,
                    title="Seat Swap Partially Approved",
                    message=f"One manager has approved seat swap #{req.id}; waiting for the second manager's approval.",
                    type=NOTIFICATION_TYPE_APPROVAL,
                )

            return SeatRequestService._to_response(req)

        req.status = REQUEST_STATUS_MANAGER_APPROVED
        req.approved_by = current_user.employee_id
        req.approved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(req)

        NotificationService.notify_employee(
            db=db,
            employee_id=req.employee_id,
            title="Request Approved by Manager",
            message=f"Your {req.request_type} request #{req.id} was approved by manager and queued for operational fulfillment.",
            type=NOTIFICATION_TYPE_APPROVAL,
        )

        is_asset = req.request_type in (
            REQUEST_TYPE_ASSET_NEW,
            REQUEST_TYPE_ASSET_MAINTENANCE,
            REQUEST_TYPE_ASSET_REPLACEMENT,
        )
        queue_name = "Admin/IT Asset Queue" if is_asset else "Admin/Ops Seating Queue"
        NotificationService.notify_admins(
            db=db,
            title=f"New Task in {queue_name}",
            message=f"Approved {req.request_type} request #{req.id} is ready for execution.",
            type=NOTIFICATION_TYPE_APPROVAL,
        )

        return SeatRequestService._to_response(req)

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
                detail=f"Request #{request_id} not found",
            )

        if req.status != REQUEST_STATUS_MANAGER_APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot execute request #{request_id} with status '{req.status}'. It must be '{REQUEST_STATUS_MANAGER_APPROVED}'.",
            )

        details = dict(req.details or {})

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
            NotificationService.notify_employee(
                db=db,
                employee_id=req.employee_id,
                title="Seat Assigned",
                message=f"Your seat request has been completed! Desk #{seat_id} is now assigned to you.",
                type=NOTIFICATION_TYPE_EXECUTION,
            )

        elif req.request_type == REQUEST_TYPE_RELOCATION:
            from_seat = SeatRepository.get_by_employee_id(db, req.employee_id)
            if not from_seat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee currently has no active seat to relocate from",
                )
            to_seat_id = exec_data.seat_id or details.get("target_seat_id") or details.get("preferred_seat_id")
            if not to_seat_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A destination seat must be specified to execute this relocation",
                )
            SeatService.relocate_seat(
                db=db,
                current_seat_id=from_seat.id,
                target_seat_id=int(to_seat_id),
                user_id=current_user.id,
                notes=exec_data.notes or f"Executed relocation request #{req.id}",
            )
            NotificationService.notify_employee(
                db=db,
                employee_id=req.employee_id,
                title="Seat Relocation Completed",
                message=f"Your seat relocation request has been executed! You are now moved to your new desk.",
                type=NOTIFICATION_TYPE_EXECUTION,
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
                seat_id=seat_a.id,
                target_employee_id=int(target_emp_id),
                user_id=current_user.id,
                notes=exec_data.notes or f"Executed seat swap request #{req.id}",
            )
            NotificationService.notify_employee(
                db=db,
                employee_id=req.employee_id,
                title="Seat Swap Executed",
                message=f"Your seat swap is complete! You are now assigned to desk {seat_b.seat_number}.",
                type=NOTIFICATION_TYPE_EXECUTION,
            )
            NotificationService.notify_employee(
                db=db,
                employee_id=int(target_emp_id),
                title="Seat Swap Executed",
                message=f"Your seat swap is complete! You are now assigned to desk {seat_a.seat_number}.",
                type=NOTIFICATION_TYPE_EXECUTION,
            )

        elif req.request_type == REQUEST_TYPE_ASSET_NEW:
            target_asset_id = exec_data.asset_id or details.get("asset_id")
            if not target_asset_id:
                req_asset_type = details.get("asset_type")
                available_assets = AssetRepository.get_all(db, status="Available", asset_type=req_asset_type)
                if not available_assets:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No available '{req_asset_type}' asset in inventory. Please add an asset first.",
                    )
                target_asset_id = available_assets[0].id

            AssetService.allocate_asset(
                db=db,
                asset_id=int(target_asset_id),
                data=AssetAllocate(
                    employee_id=req.employee_id,
                    notes=exec_data.notes or f"Fulfilled asset request #{req.id}",
                ),
                current_user=current_user,
            )
            details["fulfilled_asset_id"] = target_asset_id
            NotificationService.notify_employee(
                db=db,
                employee_id=req.employee_id,
                title="Asset Request Fulfilled",
                message=f"Your {details.get('asset_type', 'asset')} request #{req.id} has been fulfilled and allocated to you.",
                type=NOTIFICATION_TYPE_EXECUTION,
            )

        elif req.request_type == REQUEST_TYPE_ASSET_MAINTENANCE:
            target_asset_id = exec_data.asset_id or details.get("current_asset_id")
            if not target_asset_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Asset ID to maintain is required",
                )
            AssetService.set_maintenance(
                db=db,
                asset_id=int(target_asset_id),
                data=AssetMaintenance(
                    notes=exec_data.notes or f"Maintenance completed for request #{req.id}",
                ),
                current_user=current_user,
            )
            NotificationService.notify_employee(
                db=db,
                employee_id=req.employee_id,
                title="Asset Maintenance Recorded",
                message=f"Maintenance for your asset request #{req.id} has been recorded by IT.",
                type=NOTIFICATION_TYPE_EXECUTION,
            )

        elif req.request_type == REQUEST_TYPE_ASSET_REPLACEMENT:
            old_asset_id = exec_data.asset_id or details.get("current_asset_id")
            new_asset_id = exec_data.replacement_asset_id
            if not old_asset_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current asset ID to replace is required",
                )
            if not new_asset_id:
                req_asset_type = details.get("asset_type")
                available_assets = AssetRepository.get_all(db, status="Available", asset_type=req_asset_type)
                if not available_assets:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No replacement '{req_asset_type}' asset available in inventory.",
                    )
                new_asset_id = available_assets[0].id

            AssetService.replace_asset(
                db=db,
                asset_id=int(old_asset_id),
                data=AssetReplace(
                    replacement_asset_id=int(new_asset_id),
                    notes=exec_data.notes or f"Replacement executed for request #{req.id}",
                ),
                current_user=current_user,
            )
            details["replaced_with_asset_id"] = new_asset_id
            NotificationService.notify_employee(
                db=db,
                employee_id=req.employee_id,
                title="Asset Replaced",
                message=f"Your replacement request #{req.id} has been fulfilled by IT.",
                type=NOTIFICATION_TYPE_EXECUTION,
            )

        req.status = REQUEST_STATUS_COMPLETED
        req.assigned_to = current_user.employee_id
        req.completed_at = datetime.now(timezone.utc)
        req.details = details
        db.commit()
        db.refresh(req)

        return SeatRequestService._to_response(req)
