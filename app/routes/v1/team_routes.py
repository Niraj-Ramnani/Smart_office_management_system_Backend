from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.controllers.team_controller import TeamController
from app.core.constants import ROLE_ADMIN, ROLE_MANAGER
from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamMemberAddRequest,
    TeamResponse,
    TeamUpdate,
)

router = APIRouter(prefix="/teams", tags=["Teams"])


def _check_team_management_permission(team_id: int, user: User, db: Session) -> None:
    if user.role and user.role.name == ROLE_ADMIN:
        return
    if user.role and user.role.name == ROLE_MANAGER:
        team = TeamController.get_team(db, team_id)
        if user.employee_id and team.manager_id == user.employee_id:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to manage this team",
    )


@router.get("", response_model=list[TeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[TeamResponse]:
    return TeamController.list_teams(db)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TeamResponse:
    return TeamController.get_team(db, team_id)


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> TeamResponse:
    return TeamController.create_team(db, data)


@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    data: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamResponse:
    _check_team_management_permission(team_id, current_user, db)
    return TeamController.update_team(db, team_id, data)


@router.delete("/{team_id}")
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    return TeamController.delete_team(db, team_id)


@router.post("/{team_id}/members", response_model=TeamResponse)
def add_team_members(
    team_id: int,
    data: TeamMemberAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamResponse:
    _check_team_management_permission(team_id, current_user, db)
    return TeamController.add_members(db, team_id, data.employee_ids)


@router.delete("/{team_id}/members/{employee_id}", response_model=TeamResponse)
def remove_team_member(
    team_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamResponse:
    _check_team_management_permission(team_id, current_user, db)
    return TeamController.remove_member(db, team_id, employee_id)
