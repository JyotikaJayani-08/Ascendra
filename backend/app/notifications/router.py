"""
Ascendra — Notification Router.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import MessageResponse
from app.core.dependencies import get_current_active_user, get_user_from_query_token
from app.core.exceptions import TokenInvalid
from app.database import get_db
from app.notifications.schemas import NotificationResponse
from app.notifications.service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications (paginated)."""
    if unread_only:
        items = await notification_service.list_unread(db=db, user_id=user.id)
    else:
        items = await notification_service.list_all(db=db, user_id=user.id)
    # Apply pagination
    start = (page - 1) * page_size
    return [NotificationResponse.model_validate(n) for n in items[start:start + page_size]]


@router.post("/{notification_id}/read", response_model=MessageResponse)
async def mark_read(
    notification_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    await notification_service.mark_read(
        db=db, notification_id=notification_id, user_id=user.id
    )
    return MessageResponse(message="Notification marked as read.")


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_read(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    await notification_service.mark_all_read(db=db, user_id=user.id)
    return MessageResponse(message="All notifications marked as read.")


@router.get("/stream")
async def stream_notifications(
    token: str = Query(None, description="Access token for EventSource compatibility"),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events (SSE) endpoint for live notifications."""
    if not token:
        raise TokenInvalid()

    current_user = await get_user_from_query_token(token=token, db=db)
    user_id = str(current_user.id)

    return StreamingResponse(
        notification_service.stream_notifications(user_id),
        media_type="text/event-stream",
    )
