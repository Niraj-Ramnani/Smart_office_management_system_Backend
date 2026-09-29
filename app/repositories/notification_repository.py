from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.notification import Notification

class NotificationRepository:
    @staticmethod
    def get_by_id(db: Session, notification_id: int) -> Notification | None:
        return db.query(Notification).filter(Notification.id == notification_id).first()

    @staticmethod
    def get_by_user(db: Session, user_id: int, limit: int = 50) -> list[Notification]:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_unread(db: Session, user_id: int) -> int:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .count()
        )

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        type: str,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            is_read=False,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int) -> Notification | None:
        notif = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if notif:
            notif.is_read = True
            db.commit()
            db.refresh(notif)
        return notif

    @staticmethod
    def delete(db: Session, notification_id: int, user_id: int) -> bool:
        notif = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if notif:
            db.delete(notif)
            db.commit()
            return True
        return False

    @staticmethod
    def delete_all(db: Session, user_id: int) -> int:
        count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .delete()
        )
        db.commit()
        return count

    @staticmethod
    def mark_all_as_read(db: Session, user_id: int) -> int:
        count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .delete()
        )
        db.commit()
        return count
