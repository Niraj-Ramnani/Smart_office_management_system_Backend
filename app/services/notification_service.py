import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationResponse, NotificationSummary

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
        self.all_connections: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def get_loop(self) -> asyncio.AbstractEventLoop | None:
        if self._loop and not self._loop.is_closed():
            return self._loop
        try:
            loop = asyncio.get_running_loop()
            self._loop = loop
            return loop
        except RuntimeError:
            return None

    async def connect(self, websocket: WebSocket, user_id: int | None = None):
        self.set_loop(asyncio.get_running_loop())
        await websocket.accept()
        if websocket not in self.all_connections:
            self.all_connections.append(websocket)
        if user_id is not None:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            if websocket not in self.active_connections[user_id]:
                self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int | None = None):
        if websocket in self.all_connections:
            self.all_connections.remove(websocket)
        if user_id is not None and user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        for uid in list(self.active_connections.keys()):
            if websocket in self.active_connections[uid]:
                self.active_connections[uid].remove(websocket)
                if not self.active_connections[uid]:
                    del self.active_connections[uid]

    async def send_personal_message(self, message: dict[str, Any], user_id: int):
        if user_id in self.active_connections:
            text = json.dumps(message, default=str)
            dead_connections = []
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_text(text)
                except Exception:
                    dead_connections.append(connection)
            for dead in dead_connections:
                self.disconnect(dead, user_id)

    async def broadcast(self, message: dict[str, Any]):
        text = json.dumps(message, default=str)
        dead_connections = []
        for connection in list(self.all_connections):
            try:
                await connection.send_text(text)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

    def send_personal_message_threadsafe(self, message: dict[str, Any], user_id: int):
        loop = self.get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.send_personal_message(message, user_id), loop)

    def broadcast_threadsafe(self, message: dict[str, Any]):
        loop = self.get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)

    def broadcast_entity_change(
        self,
        entity: str,
        action: str = "updated",
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        payload = {
            "event": "DATA_CHANGED",
            "type": "REFRESH",
            "entity": entity,
            "action": action,
            "tags": tags or [entity],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            payload.update(extra)
        self.broadcast_threadsafe(payload)

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
        unread = NotificationRepository.count_unread(db, user_id)
        ws_manager.send_personal_message_threadsafe({
            "event": "NOTIFICATION_UPDATE",
            "type": "NOTIFICATION",
            "unread_count": unread,
            "tags": ["Notification"],
        }, user_id)
        return NotificationService._to_response(notif) if notif else None

    @staticmethod
    def mark_all_as_read(db: Session, user_id: int) -> int:
        count = NotificationRepository.mark_all_as_read(db, user_id)
        ws_manager.send_personal_message_threadsafe({
            "event": "NOTIFICATION_UPDATE",
            "type": "NOTIFICATION",
            "unread_count": 0,
            "tags": ["Notification"],
        }, user_id)
        return count

    @staticmethod
    def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
        res = NotificationRepository.delete(db, notification_id, user_id)
        unread = NotificationRepository.count_unread(db, user_id)
        ws_manager.send_personal_message_threadsafe({
            "event": "NOTIFICATION_UPDATE",
            "type": "NOTIFICATION",
            "unread_count": unread,
            "tags": ["Notification"],
        }, user_id)
        return res

    @staticmethod
    def delete_all(db: Session, user_id: int) -> int:
        count = NotificationRepository.delete_all(db, user_id)
        ws_manager.send_personal_message_threadsafe({
            "event": "NOTIFICATION_UPDATE",
            "type": "NOTIFICATION",
            "unread_count": 0,
            "tags": ["Notification"],
        }, user_id)
        return count

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
            "type": "NOTIFICATION",
            "notification_type": type,
            "id": notif.id,
            "title": title,
            "message": message,
            "is_read": False,
            "created_at": notif.created_at.isoformat() if notif.created_at else datetime.now(timezone.utc).isoformat(),
            "unread_count": unread,
            "tags": ["Notification", "SeatRequest", "Seat", "Asset", "Employee"],
        }
        ws_manager.send_personal_message_threadsafe(payload, user_id)
        ws_manager.broadcast_entity_change(
            entity="Notification",
            action="created",
            tags=["Notification", "SeatRequest", "Seat", "Asset", "Employee"],
        )
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
