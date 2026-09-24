from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.building import Building


class BuildingRepository:
    @staticmethod
    def get_all(db: Session) -> list[Building]:
        return (
            db.query(Building)
            .options(joinedload(Building.floors))
            .order_by(Building.name)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, building_id: int) -> Building | None:
        return (
            db.query(Building)
            .options(joinedload(Building.floors))
            .filter(Building.id == building_id)
            .first()
        )

    @staticmethod
    def get_by_code(
        db: Session, code: str, exclude_id: int | None = None
    ) -> Building | None:
        query = db.query(Building).filter(func.lower(Building.code) == code.strip().lower())
        if exclude_id is not None:
            query = query.filter(Building.id != exclude_id)
        return query.first()

    @staticmethod
    def create(
        db: Session, name: str, code: str, address: str | None = None
    ) -> Building:
        building = Building(
            name=name.strip(),
            code=code.strip(),
            address=address.strip() if address else None,
        )
        db.add(building)
        db.commit()
        db.refresh(building)
        return building

    @staticmethod
    def update(
        db: Session,
        building: Building,
        name: str | None = None,
        code: str | None = None,
        address: str | None = None,
    ) -> Building:
        if name is not None:
            building.name = name.strip()
        if code is not None:
            building.code = code.strip()
        if address is not None:
            building.address = address.strip() if address else None

        db.commit()
        db.refresh(building)
        return building

    @staticmethod
    def delete(db: Session, building: Building) -> None:
        db.delete(building)
        db.commit()
