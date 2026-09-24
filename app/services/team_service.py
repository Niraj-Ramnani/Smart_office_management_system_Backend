from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.team import Team
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.team_repository import TeamRepository
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate


class TeamService:
    @staticmethod
    def list_teams(db: Session) -> list[TeamResponse]:
        teams = TeamRepository.get_all(db)
        result = []
        for t in teams:
            res = TeamResponse.model_validate(t)
            if t.manager:
                res.manager_name = f"{t.manager.first_name} {t.manager.last_name}"
                res.manager_email = t.manager.email
            res.member_count = len(t.employees) if t.employees else 0
            result.append(res)
        return result

    @staticmethod
    def get_team(db: Session, team_id: int) -> Team:
        team = TeamRepository.get_by_id(db, team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {team_id} not found",
            )
        return team

    @staticmethod
    def get_team_response(db: Session, team_id: int) -> TeamResponse:
        team = TeamService.get_team(db, team_id)
        res = TeamResponse.model_validate(team)
        if team.manager:
            res.manager_name = f"{team.manager.first_name} {team.manager.last_name}"
            res.manager_email = team.manager.email
        res.member_count = len(team.employees) if team.employees else 0
        return res

    @staticmethod
    def create_team(db: Session, data: TeamCreate) -> TeamResponse:
        manager = EmployeeRepository.get_by_id(db, data.manager_id)
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected manager does not exist. An employee must be created first.",
            )

        team = TeamRepository.create(
            db,
            name=data.name.strip(),
            department=data.department.strip(),
            manager_id=data.manager_id,
        )

        res = TeamResponse.model_validate(team)
        res.manager_name = f"{manager.first_name} {manager.last_name}"
        res.manager_email = manager.email
        res.member_count = 0
        return res

    @staticmethod
    def update_team(db: Session, team_id: int, data: TeamUpdate) -> TeamResponse:
        team = TeamService.get_team(db, team_id)

        if data.manager_id is not None:
            manager = EmployeeRepository.get_by_id(db, data.manager_id)
            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected manager does not exist",
                )

        updated = TeamRepository.update(
            db,
            team,
            name=data.name.strip() if data.name is not None else None,
            department=data.department.strip() if data.department is not None else None,
            manager_id=data.manager_id,
        )

        res = TeamResponse.model_validate(updated)
        if updated.manager:
            res.manager_name = f"{updated.manager.first_name} {updated.manager.last_name}"
            res.manager_email = updated.manager.email
        res.member_count = len(updated.employees) if updated.employees else 0
        return res

    @staticmethod
    def delete_team(db: Session, team_id: int) -> dict[str, str]:
        team = TeamService.get_team(db, team_id)
        if team.employees and len(team.employees) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete team '{team.name}' while employees are assigned to it.",
            )
        TeamRepository.delete(db, team)
        return {"message": f"Team '{team.name}' deleted successfully"}
