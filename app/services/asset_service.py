from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import (
    ASSET_STATUS_ASSIGNED,
    ASSET_STATUS_AVAILABLE,
    ASSET_STATUS_RETIRED,
    ASSET_STATUS_UNDER_MAINTENANCE,
    ASSET_TYPES,
    NOTIFICATION_TYPE_ASSET,
)
from app.models.activity_log import ActivityLog
from app.models.asset import Asset
from app.models.asset_allocation import AssetAllocation
from app.models.employee import Employee
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.schemas.asset import (
    AssetAllocate,
    AssetAllocationResponse,
    AssetCreate,
    AssetMaintenance,
    AssetReplace,
    AssetResponse,
    AssetReturn,
    AssetUpdate,
)
from app.services.notification_service import NotificationService


class AssetService:
    @staticmethod
    def _to_response(asset: Asset) -> AssetResponse:
        emp_id = None
        emp_name = None
        emp_code = None
        active_alloc = next(
            (a for a in asset.asset_allocations if a.status == "ACTIVE"), None
        )
        if active_alloc and active_alloc.employee:
            emp_id = active_alloc.employee.id
            emp_name = f"{active_alloc.employee.first_name} {active_alloc.employee.last_name}"
            emp_code = active_alloc.employee.employee_code

        return AssetResponse(
            id=asset.id,
            asset_code=asset.asset_code,
            asset_type=asset.asset_type,
            name=asset.name,
            serial_number=asset.serial_number,
            status=asset.status,
            purchase_date=asset.purchase_date,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            current_employee_id=emp_id,
            current_employee_name=emp_name,
            current_employee_code=emp_code,
        )

    @staticmethod
    def _to_allocation_response(alloc: AssetAllocation) -> AssetAllocationResponse:
        a_code = alloc.asset.asset_code if alloc.asset else None
        a_type = alloc.asset.asset_type if alloc.asset else None
        a_name = alloc.asset.name if alloc.asset else None
        e_name = None
        e_code = None
        if alloc.employee:
            e_name = f"{alloc.employee.first_name} {alloc.employee.last_name}"
            e_code = alloc.employee.employee_code

        return AssetAllocationResponse(
            id=alloc.id,
            asset_id=alloc.asset_id,
            employee_id=alloc.employee_id,
            action=alloc.action,
            allocated_at=alloc.allocated_at,
            returned_at=alloc.returned_at,
            status=alloc.status,
            notes=alloc.notes,
            created_at=alloc.created_at,
            asset_code=a_code,
            asset_type=a_type,
            asset_name=a_name,
            employee_name=e_name,
            employee_code=e_code,
        )

    @staticmethod
    def get_all(
        db: Session,
        status: str | None = None,
        asset_type: str | None = None,
        search: str | None = None,
    ) -> list[AssetResponse]:
        assets = AssetRepository.get_all(db, status=status, asset_type=asset_type, search=search)
        return [AssetService._to_response(a) for a in assets]

    @staticmethod
    def get_by_id(db: Session, asset_id: int) -> AssetResponse:
        asset = AssetRepository.get_by_id(db, asset_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset #{asset_id} not found",
            )
        return AssetService._to_response(asset)

    @staticmethod
    def get_my_assets(db: Session, current_user: User) -> list[AssetAllocationResponse]:
        if not current_user.employee_id:
            return []
        allocations = AssetRepository.get_active_allocations_by_employee(
            db, current_user.employee_id
        )
        return [AssetService._to_allocation_response(a) for a in allocations]

    @staticmethod
    def get_employee_assets(db: Session, employee_id: int) -> list[AssetAllocationResponse]:
        allocations = AssetRepository.get_active_allocations_by_employee(
            db, employee_id
        )
        return [AssetService._to_allocation_response(a) for a in allocations]

    @staticmethod
    def create_asset(
        db: Session,
        data: AssetCreate,
        current_user: User,
    ) -> AssetResponse:
        code_clean = data.asset_code.strip()
        serial_clean = data.serial_number.strip()

        if AssetRepository.get_by_code(db, code_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with code '{code_clean}' already exists",
            )
        if AssetRepository.get_by_serial(db, serial_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with serial number '{serial_clean}' already exists",
            )

        asset = AssetRepository.create_asset(
            db=db,
            asset_code=code_clean,
            asset_type=data.asset_type.strip(),
            name=data.name.strip(),
            serial_number=serial_clean,
            purchase_date=data.purchase_date,
        )

        log = ActivityLog(
            user_id=current_user.id,
            action="CREATE",
            entity_type="ASSET",
            entity_id=asset.id,
            description=f"Created asset {asset.asset_code} ({asset.name})",
        )
        db.add(log)
        db.commit()

        return AssetService._to_response(asset)

    @staticmethod
    def allocate_asset(
        db: Session,
        asset_id: int,
        data: AssetAllocate,
        current_user: User,
    ) -> AssetResponse:
        asset = AssetRepository.get_by_id(db, asset_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset #{asset_id} not found",
            )
        if asset.status != ASSET_STATUS_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset '{asset.asset_code}' is currently '{asset.status}' and cannot be allocated. It must be 'Available'.",
            )

        employee = db.query(Employee).filter(Employee.id == data.employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee #{data.employee_id} not found",
            )

        AssetRepository.allocate_asset(
            db=db,
            asset=asset,
            employee_id=employee.id,
            notes=data.notes,
        )

        log = ActivityLog(
            user_id=current_user.id,
            action="ALLOCATE",
            entity_type="ASSET",
            entity_id=asset.id,
            description=f"Allocated asset {asset.asset_code} to {employee.first_name} {employee.last_name}",
        )
        db.add(log)
        db.commit()

        NotificationService.notify_employee(
            db=db,
            employee_id=employee.id,
            title="New Asset Allocated",
            message=f"{asset.asset_type} '{asset.name}' ({asset.asset_code}) has been allocated to you.",
            type=NOTIFICATION_TYPE_ASSET,
        )

        return AssetService._to_response(asset)

    @staticmethod
    def return_asset(
        db: Session,
        asset_id: int,
        data: AssetReturn,
        current_user: User,
    ) -> AssetResponse:
        asset = AssetRepository.get_by_id(db, asset_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset #{asset_id} not found",
            )
        if asset.status != ASSET_STATUS_ASSIGNED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset '{asset.asset_code}' is not currently assigned",
            )

        active_alloc = AssetRepository.get_active_allocation(db, asset.id)
        emp_id = active_alloc.employee_id if active_alloc else None

        AssetRepository.return_asset(
            db=db,
            asset=asset,
            notes=data.notes,
        )

        log = ActivityLog(
            user_id=current_user.id,
            action="RETURN",
            entity_type="ASSET",
            entity_id=asset.id,
            description=f"Returned asset {asset.asset_code}",
        )
        db.add(log)
        db.commit()

        if emp_id:
            NotificationService.notify_employee(
                db=db,
                employee_id=emp_id,
                title="Asset Returned",
                message=f"Asset {asset.name} ({asset.asset_code}) has been recorded as returned.",
                type=NOTIFICATION_TYPE_ASSET,
            )

        return AssetService._to_response(asset)

    @staticmethod
    def set_maintenance(
        db: Session,
        asset_id: int,
        data: AssetMaintenance,
        current_user: User,
    ) -> AssetResponse:
        asset = AssetRepository.get_by_id(db, asset_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset #{asset_id} not found",
            )

        AssetRepository.set_maintenance(
            db=db,
            asset=asset,
            notes=data.notes,
        )

        log = ActivityLog(
            user_id=current_user.id,
            action="MAINTENANCE",
            entity_type="ASSET",
            entity_id=asset.id,
            description=f"Marked asset {asset.asset_code} as Under Maintenance",
        )
        db.add(log)
        db.commit()

        return AssetService._to_response(asset)

    @staticmethod
    def replace_asset(
        db: Session,
        asset_id: int,
        data: AssetReplace,
        current_user: User,
    ) -> AssetResponse:
        old_asset = AssetRepository.get_by_id(db, asset_id)
        if not old_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Original asset #{asset_id} not found",
            )
        new_asset = AssetRepository.get_by_id(db, data.replacement_asset_id)
        if not new_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Replacement asset #{data.replacement_asset_id} not found",
            )
        if new_asset.status != ASSET_STATUS_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Replacement asset '{new_asset.asset_code}' is '{new_asset.status}' and not available",
            )

        active_alloc = AssetRepository.get_active_allocation(db, old_asset.id)
        if not active_alloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Original asset '{old_asset.asset_code}' has no active allocation to replace",
            )
        emp_id = active_alloc.employee_id

        AssetRepository.return_asset(db, old_asset, notes=f"Replaced by {new_asset.asset_code}. {data.notes or ''}")
        AssetRepository.allocate_asset(db, new_asset, emp_id, notes=f"Replacement for {old_asset.asset_code}. {data.notes or ''}")

        log = ActivityLog(
            user_id=current_user.id,
            action="REPLACE",
            entity_type="ASSET",
            entity_id=new_asset.id,
            description=f"Replaced asset {old_asset.asset_code} with {new_asset.asset_code}",
        )
        db.add(log)
        db.commit()

        NotificationService.notify_employee(
            db=db,
            employee_id=emp_id,
            title="Asset Replaced",
            message=f"Your {old_asset.asset_type} ({old_asset.asset_code}) has been replaced with {new_asset.name} ({new_asset.asset_code}).",
            type=NOTIFICATION_TYPE_ASSET,
        )

        return AssetService._to_response(new_asset)

    @staticmethod
    def get_asset_history(db: Session, asset_id: int) -> list[AssetAllocationResponse]:
        allocations = AssetRepository.get_allocations_for_asset(db, asset_id)
        return [AssetService._to_allocation_response(a) for a in allocations]
