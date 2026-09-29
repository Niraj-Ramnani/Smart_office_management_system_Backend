from sqlalchemy.orm import Session

from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.services.notification_service import ws_manager
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
        res = TeamService.create_team(db, data)
        ws_manager.broadcast_entity_change("Team", "created", ["Team", "Employee"])
        return res

    @staticmethod
    def update_team(
        db: Session, team_id: int, data: TeamUpdate
    ) -> TeamResponse:
        res = TeamService.update_team(db, team_id, data)
        ws_manager.broadcast_entity_change("Team", "updated", ["Team", "Employee"])
        return res

    @staticmethod
    def delete_team(db: Session, team_id: int) -> dict[str, str]:
        res = TeamService.delete_team(db, team_id)
        ws_manager.broadcast_entity_change("Team", "deleted", ["Team", "Employee"])
        return res

    @staticmethod
    def add_members(
        db: Session, team_id: int, employee_ids: list[int]
    ) -> TeamResponse:
        res = TeamService.add_members(db, team_id, employee_ids)
        ws_manager.broadcast_entity_change("Team", "members_updated", ["Team", "Employee"])
        return res

    @staticmethod
    def remove_member(
        db: Session, team_id: int, employee_id: int
    ) -> TeamResponse:
        res = TeamService.remove_member(db, team_id, employee_id)
        ws_manager.broadcast_entity_change("Team", "members_updated", ["Team", "Employee"])
        return res
