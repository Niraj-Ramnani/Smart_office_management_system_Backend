from datetime import datetime, timezone
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.core.constants import (
    ASSET_ACTION_ASSIGN,
    ASSET_ACTION_MAINTENANCE,
    ASSET_ACTION_RETURN,
    ASSET_STATUS_ASSIGNED,
    ASSET_STATUS_AVAILABLE,
    ASSET_STATUS_UNDER_MAINTENANCE,
)
from app.models.asset import Asset
from app.models.asset_allocation import AssetAllocation

class AssetRepository:
    @staticmethod
    def get_by_id(db: Session, asset_id: int) -> Asset | None:
        return (
            db.query(Asset)
            .options(
                joinedload(Asset.asset_allocations).joinedload(AssetAllocation.employee)
            )
            .filter(Asset.id == asset_id)
            .first()
        )

    @staticmethod
    def get_by_code(db: Session, asset_code: str) -> Asset | None:
        return db.query(Asset).filter(Asset.asset_code == asset_code).first()

    @staticmethod
    def get_by_serial(db: Session, serial_number: str) -> Asset | None:
        return db.query(Asset).filter(Asset.serial_number == serial_number).first()

    @staticmethod
    def get_all(
        db: Session,
        status: str | None = None,
        asset_type: str | None = None,
        search: str | None = None,
    ) -> list[Asset]:
        query = db.query(Asset).options(
            joinedload(Asset.asset_allocations).joinedload(AssetAllocation.employee)
        )
        if status:
            query = query.filter(Asset.status == status)
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        if search:
            s = f"%{search}%"
            query = query.filter(
                (Asset.asset_code.ilike(s))
                | (Asset.name.ilike(s))
                | (Asset.serial_number.ilike(s))
                | (Asset.asset_type.ilike(s))
            )
        return query.order_by(Asset.asset_type, Asset.asset_code).all()

    @staticmethod
    def get_active_allocations_by_employee(
        db: Session, employee_id: int
    ) -> list[AssetAllocation]:
        return (
            db.query(AssetAllocation)
            .options(
                joinedload(AssetAllocation.asset),
                joinedload(AssetAllocation.employee),
            )
            .filter(
                AssetAllocation.employee_id == employee_id,
                AssetAllocation.status == "ACTIVE",
            )
            .order_by(desc(AssetAllocation.allocated_at))
            .all()
        )

    @staticmethod
    def get_allocations_for_asset(
        db: Session, asset_id: int
    ) -> list[AssetAllocation]:
        return (
            db.query(AssetAllocation)
            .options(
                joinedload(AssetAllocation.asset),
                joinedload(AssetAllocation.employee),
            )
            .filter(AssetAllocation.asset_id == asset_id)
            .order_by(desc(AssetAllocation.allocated_at))
            .all()
        )

    @staticmethod
    def get_active_allocation(db: Session, asset_id: int) -> AssetAllocation | None:
        return (
            db.query(AssetAllocation)
            .options(joinedload(AssetAllocation.employee))
            .filter(
                AssetAllocation.asset_id == asset_id,
                AssetAllocation.status == "ACTIVE",
            )
            .order_by(desc(AssetAllocation.allocated_at))
            .first()
        )

    @staticmethod
    def create_asset(
        db: Session,
        asset_code: str,
        asset_type: str,
        name: str,
        serial_number: str,
        purchase_date=None,
    ) -> Asset:
        asset = Asset(
            asset_code=asset_code,
            asset_type=asset_type,
            name=name,
            serial_number=serial_number,
            status=ASSET_STATUS_AVAILABLE,
            purchase_date=purchase_date,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def allocate_asset(
        db: Session,
        asset: Asset,
        employee_id: int,
        notes: str | None = None,
    ) -> AssetAllocation:
        now = datetime.now(timezone.utc)
        asset.status = ASSET_STATUS_ASSIGNED
        allocation = AssetAllocation(
            asset_id=asset.id,
            employee_id=employee_id,
            action=ASSET_ACTION_ASSIGN,
            allocated_at=now,
            status="ACTIVE",
            notes=notes,
        )
        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        return allocation

    @staticmethod
    def return_asset(
        db: Session,
        asset: Asset,
        notes: str | None = None,
    ) -> AssetAllocation | None:
        now = datetime.now(timezone.utc)
        active_alloc = AssetRepository.get_active_allocation(db, asset.id)
        if active_alloc:
            active_alloc.returned_at = now
            active_alloc.status = "RETURNED"
            if notes:
                active_alloc.notes = (
                    f"{active_alloc.notes}\nReturn note: {notes}"
                    if active_alloc.notes
                    else notes
                )
        asset.status = ASSET_STATUS_AVAILABLE
        db.commit()
        if active_alloc:
            db.refresh(active_alloc)
        return active_alloc

    @staticmethod
    def set_maintenance(
        db: Session,
        asset: Asset,
        notes: str | None = None,
    ) -> AssetAllocation | None:
        now = datetime.now(timezone.utc)
        active_alloc = AssetRepository.get_active_allocation(db, asset.id)
        if active_alloc:
            active_alloc.returned_at = now
            active_alloc.status = "MAINTENANCE"
        asset.status = ASSET_STATUS_UNDER_MAINTENANCE
        maintenance_alloc = AssetAllocation(
            asset_id=asset.id,
            employee_id=active_alloc.employee_id if active_alloc else 0,
            action=ASSET_ACTION_MAINTENANCE,
            allocated_at=now,
            status="MAINTENANCE",
            notes=notes,
        )
        db.add(maintenance_alloc)
        db.commit()
        db.refresh(maintenance_alloc)
        return maintenance_alloc
