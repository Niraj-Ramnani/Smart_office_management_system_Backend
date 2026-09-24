from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.controllers.employee_controller import EmployeeController
from app.core.constants import ROLE_ADMIN, ROLE_MANAGER
from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user, require_admin, require_role
from app.models.user import User
from app.schemas.employee import (
    CSVImportSummaryResponse,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    search: str | None = Query(None, description="Search by name, email, code, designation"),
    department: str | None = Query(None, description="Filter by department"),
    team_id: int | None = Query(None, description="Filter by team ID"),
    employee_status: str | None = Query(None, description="Filter by status (e.g. ACTIVE, INACTIVE)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(ROLE_ADMIN, ROLE_MANAGER)),
) -> list[EmployeeResponse]:
    return EmployeeController.list_employees(
        db,
        search=search,
        department=department,
        team_id=team_id,
        employee_status=employee_status,
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeResponse:
    return EmployeeController.get_employee(db, employee_id, current_user)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EmployeeResponse:
    return EmployeeController.create_employee(db, data)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EmployeeResponse:
    return EmployeeController.update_employee(db, employee_id, data)


@router.patch("/{employee_id}/status", response_model=EmployeeResponse)
def update_employee_status(
    employee_id: int,
    data: EmployeeStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EmployeeResponse:
    return EmployeeController.update_employee_status(db, employee_id, data)


@router.delete("/{employee_id}", response_model=EmployeeResponse)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EmployeeResponse:
    return EmployeeController.delete_employee(db, employee_id)


@router.post("/csv-import", response_model=CSVImportSummaryResponse)
async def import_employees_csv(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CSVImportSummaryResponse:
    return await EmployeeController.import_employees_csv(request, db)
