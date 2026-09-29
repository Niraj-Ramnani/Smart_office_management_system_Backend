from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.constants import REQUEST_STATUS_MANAGER_APPROVED, REQUEST_STATUS_PENDING
from app.models.employee import Employee
from app.models.permission_request import PermissionRequest
from app.models.team import Team

class SeatRequestRepository:
    @staticmethod
    def get_all(
        db: Session,
        status: str | None = None,
        request_type: str | None = None,
    ) -> list[PermissionRequest]:
        query = (
            db.query(PermissionRequest)
            .options(
                joinedload(PermissionRequest.employee),
                joinedload(PermissionRequest.approver),
                joinedload(PermissionRequest.assignee),
            )
        )
        if status:
            query = query.filter(PermissionRequest.status == status)
        if request_type:
            query = query.filter(PermissionRequest.request_type == request_type)
        return query.order_by(PermissionRequest.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, request_id: int) -> PermissionRequest | None:
        return (
            db.query(PermissionRequest)
            .options(
                joinedload(PermissionRequest.employee),
                joinedload(PermissionRequest.approver),
                joinedload(PermissionRequest.assignee),
            )
            .filter(PermissionRequest.id == request_id)
            .first()
        )

    @staticmethod
    def get_by_employee(
        db: Session, employee_id: int
    ) -> list[PermissionRequest]:
        return (
            db.query(PermissionRequest)
            .options(
                joinedload(PermissionRequest.employee),
                joinedload(PermissionRequest.approver),
                joinedload(PermissionRequest.assignee),
            )
            .filter(PermissionRequest.employee_id == employee_id)
            .order_by(PermissionRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_manager(
        db: Session, manager_employee_id: int, status: str | None = None
    ) -> list[PermissionRequest]:
        query = (
            db.query(PermissionRequest)
            .join(PermissionRequest.employee)
            .outerjoin(Employee.team)
            .options(
                joinedload(PermissionRequest.employee),
                joinedload(PermissionRequest.approver),
                joinedload(PermissionRequest.assignee),
            )
            .filter(
                or_(
                    Employee.manager_id == manager_employee_id,
                    Team.manager_id == manager_employee_id,
                )
            )
        )
        if status:
            query = query.filter(PermissionRequest.status == status)
        return query.order_by(PermissionRequest.created_at.desc()).all()

    @staticmethod
    def get_pending_for_manager(
        db: Session, manager_employee_id: int
    ) -> list[PermissionRequest]:
        return SeatRequestRepository.get_by_manager(
            db, manager_employee_id, status=REQUEST_STATUS_PENDING
        )

    @staticmethod
    def get_approved_for_admin(db: Session) -> list[PermissionRequest]:
        return (
            db.query(PermissionRequest)
            .options(
                joinedload(PermissionRequest.employee),
                joinedload(PermissionRequest.approver),
                joinedload(PermissionRequest.assignee),
            )
            .filter(PermissionRequest.status == REQUEST_STATUS_MANAGER_APPROVED)
            .order_by(PermissionRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        employee_id: int,
        request_type: str,
        details: dict,
    ) -> PermissionRequest:
        req = PermissionRequest(
            employee_id=employee_id,
            request_type=request_type,
            status=REQUEST_STATUS_PENDING,
            details=details,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def update(
        db: Session,
        request: PermissionRequest,
        **fields,
    ) -> PermissionRequest:
        for k, v in fields.items():
            setattr(request, k, v)
        db.commit()
        db.refresh(request)
        return request
