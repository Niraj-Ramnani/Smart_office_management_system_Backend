from sqlalchemy.orm import Session, joinedload

from app.models.team import Team


class TeamRepository:
    @staticmethod
    def get_all(db: Session) -> list[Team]:
        return (
            db.query(Team)
            .options(joinedload(Team.manager), joinedload(Team.employees))
            .order_by(Team.name)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, team_id: int) -> Team | None:
        return (
            db.query(Team)
            .options(joinedload(Team.manager), joinedload(Team.employees))
            .filter(Team.id == team_id)
            .first()
        )

    @staticmethod
    def create(db: Session, name: str, department: str, manager_id: int) -> Team:
        team = Team(
            name=name.strip(),
            department=department.strip(),
            manager_id=manager_id,
        )
        db.add(team)
        db.commit()
        db.refresh(team)
        return team

    @staticmethod
    def update(
        db: Session,
        team: Team,
        name: str | None = None,
        department: str | None = None,
        manager_id: int | None = None,
    ) -> Team:
        if name is not None:
            team.name = name.strip()
        if department is not None:
            team.department = department.strip()
        if manager_id is not None:
            team.manager_id = manager_id

        db.commit()
        db.refresh(team)
        return team

    @staticmethod
    def delete(db: Session, team: Team) -> None:
        db.delete(team)
        db.commit()
