from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse, NotificationSummary
from app.services.notification_service import NotificationService, ws_manager

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=NotificationSummary)
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationSummary:
    return NotificationService.get_summary(db, current_user.id)


@router.put("/notifications/{notification_id}/read", response_model=NotificationResponse)
@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    notif = NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not notif:
        return NotificationResponse(
            id=notification_id,
            user_id=current_user.id,
            title="",
            message="",
            type="",
            is_read=True,
            created_at=None, # type: ignore
        )
    return notif


@router.put("/notifications/read-all")
@router.post("/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = NotificationService.mark_all_as_read(db, current_user.id)
    return {"message": "All notifications marked as read and cleared", "count": count}


@router.delete("/notifications/{notification_id}")
def delete_single_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    NotificationService.delete_notification(db, notification_id, current_user.id)
    return {"message": "Notification removed"}


@router.delete("/notifications")
def clear_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = NotificationService.delete_all(db, current_user.id)
    return {"message": "All notifications cleared", "count": count}


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: int | None = Query(None),
):
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception:
        ws_manager.disconnect(websocket, user_id)
