from sqlalchemy.orm import Session

from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.services.team_service import TeamService


class TeamController:
    @staticmethod
    def list_teams(db: Session) -> list[TeamResponse]:
        return TeamService.list_teams(db)

    @staticmethod
    def get_team(db: Session, team_id: int) -> TeamResponse:
        return TeamService.get_team_response(db, team_id)

    @staticmethod
    def create_team(db: Session, data: TeamCreate) -> TeamResponse:
        return TeamService.create_team(db, data)

    @staticmethod
    def update_team(
        db: Session, team_id: int, data: TeamUpdate
    ) -> TeamResponse:
        return TeamService.update_team(db, team_id, data)

    @staticmethod
    def delete_team(db: Session, team_id: int) -> dict[str, str]:
        return TeamService.delete_team(db, team_id)
