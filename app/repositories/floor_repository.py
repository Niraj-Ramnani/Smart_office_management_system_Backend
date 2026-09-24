from sqlalchemy.orm import Session, joinedload

from app.models.floor import Floor


class FloorRepository:
    @staticmethod
    def get_all(db: Session, building_id: int | None = None) -> list[Floor]:
        query = (
            db.query(Floor)
            .options(joinedload(Floor.building), joinedload(Floor.seats))
            .order_by(Floor.floor_number)
        )
        if building_id is not None:
            query = query.filter(Floor.building_id == building_id)
        return query.all()

    @staticmethod
    def get_by_id(db: Session, floor_id: int) -> Floor | None:
        return (
            db.query(Floor)
            .options(joinedload(Floor.building), joinedload(Floor.seats))
            .filter(Floor.id == floor_id)
            .first()
        )

    @staticmethod
    def get_by_building_and_number(
        db: Session,
        building_id: int,
        floor_number: int,
        exclude_id: int | None = None,
    ) -> Floor | None:
        query = db.query(Floor).filter(
            Floor.building_id == building_id,
            Floor.floor_number == floor_number,
        )
        if exclude_id is not None:
            query = query.filter(Floor.id != exclude_id)
        return query.first()

    @staticmethod
    def create(
        db: Session,
        building_id: int,
        name: str,
        floor_number: int,
        map_width: int,
        map_height: int,
    ) -> Floor:
        floor = Floor(
            building_id=building_id,
            name=name.strip(),
            floor_number=floor_number,
            map_width=map_width,
            map_height=map_height,
        )
        db.add(floor)
        db.commit()
        db.refresh(floor)
        return floor

    @staticmethod
    def update(
        db: Session,
        floor: Floor,
        building_id: int | None = None,
        name: str | None = None,
        floor_number: int | None = None,
        map_width: int | None = None,
        map_height: int | None = None,
    ) -> Floor:
        if building_id is not None:
            floor.building_id = building_id
        if name is not None:
            floor.name = name.strip()
        if floor_number is not None:
            floor.floor_number = floor_number
        if map_width is not None:
            floor.map_width = map_width
        if map_height is not None:
            floor.map_height = map_height

        db.commit()
        db.refresh(floor)
        return floor

    @staticmethod
    def delete(db: Session, floor: Floor) -> None:
        db.delete(floor)
        db.commit()
