import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationResponse, NotificationSummary


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
        self.broadcast_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, user_id: int | None = None):
        await websocket.accept()
        if user_id:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
        else:
            self.broadcast_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int | None = None):
        if user_id and user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        if websocket in self.broadcast_connections:
            self.broadcast_connections.remove(websocket)

    async def send_personal_message(self, message: dict[str, Any], user_id: int):
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message, default=str))
                except Exception:
                    dead_connections.append(connection)
            for dead in dead_connections:
                self.disconnect(dead, user_id)

    async def broadcast(self, message: dict[str, Any]):
        dead_connections = []
        for connection in self.broadcast_connections:
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = ConnectionManager()


class NotificationService:
    @staticmethod
    def _to_response(n) -> NotificationResponse:
        return NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            title=n.title,
            message=n.message,
            type=n.type,
            is_read=n.is_read,
            created_at=n.created_at,
        )

    @staticmethod
    def get_summary(db: Session, user_id: int) -> NotificationSummary:
        notifications = NotificationRepository.get_by_user(db, user_id, limit=50)
        unread_count = NotificationRepository.count_unread(db, user_id)
        return NotificationSummary(
            unread_count=unread_count,
            notifications=[NotificationService._to_response(n) for n in notifications],
        )

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int) -> NotificationResponse | None:
        notif = NotificationRepository.mark_as_read(db, notification_id, user_id)
        return NotificationService._to_response(notif) if notif else None

    @staticmethod
    def mark_all_as_read(db: Session, user_id: int) -> int:
        return NotificationRepository.mark_all_as_read(db, user_id)

    @staticmethod
    def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
        return NotificationRepository.delete(db, notification_id, user_id)

    @staticmethod
    def delete_all(db: Session, user_id: int) -> int:
        return NotificationRepository.delete_all(db, user_id)

    @staticmethod
    def notify_user(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        type: str,
    ) -> NotificationResponse:
        notif = NotificationRepository.create(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            type=type,
        )
        unread = NotificationRepository.count_unread(db, user_id)
        payload = {
            "event": "NOTIFICATION",
            "id": notif.id,
            "title": title,
            "message": message,
            "type": type,
            "is_read": False,
            "created_at": notif.created_at.isoformat() if notif.created_at else datetime.now(timezone.utc).isoformat(),
            "unread_count": unread,
        }
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(ws_manager.send_personal_message(payload, user_id))
        except Exception:
            pass

        return NotificationService._to_response(notif)

    @staticmethod
    def notify_employee(
        db: Session,
        employee_id: int,
        title: str,
        message: str,
        type: str,
    ):
        user = db.query(User).filter(User.employee_id == employee_id).first()
        if user:
            NotificationService.notify_user(db, user.id, title, message, type)

    @staticmethod
    def notify_admins(
        db: Session,
        title: str,
        message: str,
        type: str,
    ):
        from app.models.role import Role
        from app.core.constants import ROLE_ADMIN
        admin_role = db.query(Role).filter(Role.name == ROLE_ADMIN).first()
        if admin_role:
            admins = db.query(User).filter(User.role_id == admin_role.id).all()
            for admin in admins:
                NotificationService.notify_user(db, admin.id, title, message, type)
