from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers.asset_controller import AssetController
from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user, require_admin
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

router = APIRouter(prefix="/assets", tags=["Asset Management"])


@router.get("", response_model=list[AssetResponse])
def get_all_assets(
    status: str | None = Query(None),
    asset_type: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[AssetResponse]:
    return AssetController.get_all(db, status, asset_type, search)


@router.get("/my", response_model=list[AssetAllocationResponse])
def get_my_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetAllocationResponse]:
    return AssetController.get_my_assets(db, current_user)


@router.get("/employee/{employee_id}", response_model=list[AssetAllocationResponse])
def get_employee_assets(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetAllocationResponse]:
    return AssetController.get_employee_assets(db, employee_id)


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset_by_id(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetResponse:
    return AssetController.get_by_id(db, asset_id)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AssetResponse:
    return AssetController.create_asset(db, data, current_user)


@router.post("/{asset_id}/allocate", response_model=AssetResponse)
def allocate_asset(
    asset_id: int,
    data: AssetAllocate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AssetResponse:
    return AssetController.allocate_asset(db, asset_id, data, current_user)


@router.post("/{asset_id}/return", response_model=AssetResponse)
def return_asset(
    asset_id: int,
    data: AssetReturn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AssetResponse:
    return AssetController.return_asset(db, asset_id, data, current_user)


@router.post("/{asset_id}/maintenance", response_model=AssetResponse)
def set_maintenance(
    asset_id: int,
    data: AssetMaintenance,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AssetResponse:
    return AssetController.set_maintenance(db, asset_id, data, current_user)


@router.post("/{asset_id}/replace", response_model=AssetResponse)
def replace_asset(
    asset_id: int,
    data: AssetReplace,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AssetResponse:
    return AssetController.replace_asset(db, asset_id, data, current_user)


@router.get("/{asset_id}/history", response_model=list[AssetAllocationResponse])
def get_asset_history(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetAllocationResponse]:
    return AssetController.get_asset_history(db, asset_id)
