from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.team_controller import TeamController
from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate

router = APIRouter(prefix="/teams", tags=["Teams"])


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
    _: User = Depends(require_admin),
) -> TeamResponse:
    return TeamController.update_team(db, team_id, data)


@router.delete("/{team_id}")
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    return TeamController.delete_team(db, team_id)
