from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.asset import (
    AssetAllocate,
    AssetAllocationResponse,
    AssetCreate,
    AssetMaintenance,
    AssetReplace,
    AssetResponse,
    AssetReturn,
)
from app.services.asset_service import AssetService
from app.services.notification_service import ws_manager

class AssetController:
    @staticmethod
    def get_all(
        db: Session,
        status: str | None = None,
        asset_type: str | None = None,
        search: str | None = None,
    ) -> list[AssetResponse]:
        return AssetService.get_all(db, status=status, asset_type=asset_type, search=search)

    @staticmethod
    def get_by_id(db: Session, asset_id: int) -> AssetResponse:
        return AssetService.get_by_id(db, asset_id)

    @staticmethod
    def get_my_assets(db: Session, current_user: User) -> list[AssetAllocationResponse]:
        return AssetService.get_my_assets(db, current_user)

    @staticmethod
    def get_employee_assets(db: Session, employee_id: int) -> list[AssetAllocationResponse]:
        return AssetService.get_employee_assets(db, employee_id)

    @staticmethod
    def create_asset(
        db: Session,
        data: AssetCreate,
        current_user: User,
    ) -> AssetResponse:
        res = AssetService.create_asset(db, data, current_user)
        ws_manager.broadcast_entity_change("Asset", "created", ["Asset"])
        return res

    @staticmethod
    def allocate_asset(
        db: Session,
        asset_id: int,
        data: AssetAllocate,
        current_user: User,
    ) -> AssetResponse:
        res = AssetService.allocate_asset(db, asset_id, data, current_user)
        ws_manager.broadcast_entity_change("Asset", "allocated", ["Asset", "Employee", "SeatRequest", "Notification"])
        return res

    @staticmethod
    def return_asset(
        db: Session,
        asset_id: int,
        data: AssetReturn,
        current_user: User,
    ) -> AssetResponse:
        res = AssetService.return_asset(db, asset_id, data, current_user)
        ws_manager.broadcast_entity_change("Asset", "returned", ["Asset", "Employee", "SeatRequest", "Notification"])
        return res

    @staticmethod
    def set_maintenance(
        db: Session,
        asset_id: int,
        data: AssetMaintenance,
        current_user: User,
    ) -> AssetResponse:
        res = AssetService.set_maintenance(db, asset_id, data, current_user)
        ws_manager.broadcast_entity_change("Asset", "maintenance", ["Asset", "Employee", "SeatRequest", "Notification"])
        return res

    @staticmethod
    def replace_asset(
        db: Session,
        asset_id: int,
        data: AssetReplace,
        current_user: User,
    ) -> AssetResponse:
        res = AssetService.replace_asset(db, asset_id, data, current_user)
        ws_manager.broadcast_entity_change("Asset", "replaced", ["Asset", "Employee", "SeatRequest", "Notification"])
        return res

    @staticmethod
    def get_asset_history(db: Session, asset_id: int) -> list[AssetAllocationResponse]:
        return AssetService.get_asset_history(db, asset_id)
