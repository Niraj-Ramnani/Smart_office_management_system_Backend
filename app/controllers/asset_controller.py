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
        return AssetService.create_asset(db, data, current_user)

    @staticmethod
    def allocate_asset(
        db: Session,
        asset_id: int,
        data: AssetAllocate,
        current_user: User,
    ) -> AssetResponse:
        return AssetService.allocate_asset(db, asset_id, data, current_user)

    @staticmethod
    def return_asset(
        db: Session,
        asset_id: int,
        data: AssetReturn,
        current_user: User,
    ) -> AssetResponse:
        return AssetService.return_asset(db, asset_id, data, current_user)

    @staticmethod
    def set_maintenance(
        db: Session,
        asset_id: int,
        data: AssetMaintenance,
        current_user: User,
    ) -> AssetResponse:
        return AssetService.set_maintenance(db, asset_id, data, current_user)

    @staticmethod
    def replace_asset(
        db: Session,
        asset_id: int,
        data: AssetReplace,
        current_user: User,
    ) -> AssetResponse:
        return AssetService.replace_asset(db, asset_id, data, current_user)

    @staticmethod
    def get_asset_history(db: Session, asset_id: int) -> list[AssetAllocationResponse]:
        return AssetService.get_asset_history(db, asset_id)
