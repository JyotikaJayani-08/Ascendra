"""
Ascendra — Email Router.
"""

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.schemas import MessageResponse as GenericMessage
from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.email.models import MessageStatus
from app.email.schemas import (
    ConversationResponse,
    CreateMessageRequest,
    EditMessageRequest,
    FollowUpResponse,
    MessageResponse,
    RescheduleRequest,
    ScheduleSendRequest,
)
from app.email.service import email_service
from app.email.followup_service import followup_service

logger = logging.getLogger("ascendra.email")

router = APIRouter(tags=["Email"])

# 1×1 transparent GIF pixel for open tracking
_TRACKING_PIXEL = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)


# ── Message CRUD ──────────────────────────────────────────────


@router.post("/email/draft", response_model=MessageResponse, status_code=201)
async def create_draft(
    body: CreateMessageRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a draft email for an application."""
    _, message = await email_service.create_draft(
        db=db,
        user_id=user.id,
        application_id=body.application_id,
        to_email=body.to_email,
        subject=body.subject,
        body_text=body.body_text,
        body_html=body.body_html,
        resume_version_id=body.resume_version_id,
    )
    return MessageResponse.model_validate(message)


@router.post("/email/{message_id}/approve", response_model=MessageResponse)
async def approve_message(
    message_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a draft message."""
    message = await email_service.approve_message(
        db=db, message_id=message_id, user_id=user.id
    )
    return MessageResponse.model_validate(message)


@router.post("/email/{message_id}/edit", response_model=MessageResponse)
async def edit_message(
    message_id: str,
    body: EditMessageRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit a draft/generated message before sending."""
    message = await email_service.edit_message(
        db=db,
        message_id=message_id,
        user_id=user.id,
        subject=body.subject,
        body_text=body.body_text,
        body_html=body.body_html,
    )
    return MessageResponse.model_validate(message)


@router.post("/email/{message_id}/send", response_model=MessageResponse)
@limiter.limit("20/hour")
async def queue_message(
    request: Request,
    message_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue an approved message for sending (rate limited: 20/hour)."""
    # Pre-flight check: Ensure user has configured & verified SMTP credentials
    from app.auth.models import UserEmailConfig
    stmt = select(UserEmailConfig).where(
        UserEmailConfig.user_id == user.id,
    )
    res = await db.execute(stmt)
    user_config = res.scalars().first()

    if not user_config or not user_config.is_verified:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Outreach emails cannot be sent until you configure and verify your email credentials (SMTP / App Password) in Profile Settings.",
        )

    message = await email_service.queue_message(
        db=db, message_id=message_id, user_id=user.id
    )

    # Dispatch via asyncio background task (no separate Celery worker on free tier)
    import asyncio
    from app.workers.email_tasks import _send_email_async
    asyncio.create_task(_send_email_async(message_id))

    return MessageResponse.model_validate(message)


# ── Scheduled Sending ─────────────────────────────────────────


@router.post("/email/{message_id}/schedule", response_model=MessageResponse)
async def schedule_message(
    message_id: str,
    body: ScheduleSendRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Schedule an approved message for future sending."""
    message = await email_service.schedule_message(
        db=db, message_id=message_id, user_id=user.id, scheduled_at=body.scheduled_at
    )

    # If the service decided to queue immediately (past time), dispatch now
    if message.status == "QUEUED":
        import asyncio
        from app.workers.email_tasks import _send_email_async
        asyncio.create_task(_send_email_async(message_id))

    return MessageResponse.model_validate(message)


@router.post("/email/{message_id}/reschedule", response_model=MessageResponse)
async def reschedule_message(
    message_id: str,
    body: RescheduleRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reschedule a scheduled message to a different time."""
    message = await email_service.reschedule_message(
        db=db, message_id=message_id, user_id=user.id, scheduled_at=body.scheduled_at
    )

    if message.status == "QUEUED":
        import asyncio
        from app.workers.email_tasks import _send_email_async
        asyncio.create_task(_send_email_async(message_id))

    return MessageResponse.model_validate(message)


@router.post("/email/{message_id}/cancel-schedule", response_model=MessageResponse)
async def cancel_scheduled_message(
    message_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a scheduled message (returns it to APPROVED status)."""
    message = await email_service.cancel_scheduled(
        db=db, message_id=message_id, user_id=user.id
    )
    return MessageResponse.model_validate(message)


@router.post("/email/internal/process-scheduled")
async def process_scheduled_emails(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint called by Supabase Edge Function (via pg_cron).

    Finds all SCHEDULED messages that are due and dispatches them.
    Secured via X-Internal-Secret header.
    """
    from app.config import settings
    secret = request.headers.get("X-Internal-Secret", "")
    expected = settings.JWT_SECRET  # Reuse JWT secret as internal auth
    if secret != expected:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")

    due_messages = await email_service.get_due_scheduled(db=db)

    dispatched = []
    for msg in due_messages:
        msg.status = MessageStatus.QUEUED
        msg.scheduled_at = None
        await db.commit()

        import asyncio
        from app.workers.email_tasks import _send_email_async
        asyncio.create_task(_send_email_async(str(msg.id)))

        dispatched.append(str(msg.id))

    logger.info(f"Processed {len(dispatched)} scheduled emails")
    return {"dispatched": len(dispatched), "message_ids": dispatched}


# ── Conversations ─────────────────────────────────────────────


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all conversations (paginated)."""
    convos = await email_service.get_conversations(db=db, user_id=user.id)
    # Simple offset pagination
    start = (page - 1) * page_size
    return [ConversationResponse.model_validate(c) for c in convos[start:start + page_size]]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation."""
    messages = await email_service.get_conversation_messages(
        db=db, conversation_id=conversation_id, user_id=user.id
    )
    return [MessageResponse.model_validate(m) for m in messages]


# ── Follow-ups ────────────────────────────────────────────────


@router.post("/followups/schedule", response_model=FollowUpResponse, status_code=201)
async def schedule_followup(
    conversation_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    days_after: int = Query(3, ge=1, le=30),
):
    """Schedule a follow-up email for a conversation."""
    followup = await followup_service.schedule(
        db=db,
        user_id=user.id,
        conversation_id=conversation_id,
        days_after=days_after,
    )
    return FollowUpResponse.model_validate(followup)


@router.get("/followups", response_model=list[FollowUpResponse])
async def list_pending_followups(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all pending (scheduled) follow-ups for the current user."""
    followups = await followup_service.get_pending(db=db, user_id=user.id)
    return [FollowUpResponse.model_validate(f) for f in followups]


@router.delete("/followups/{followup_id}", response_model=FollowUpResponse)
async def cancel_followup(
    followup_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a scheduled follow-up."""
    followup = await followup_service.cancel(
        db=db, followup_id=followup_id, user_id=user.id
    )
    return FollowUpResponse.model_validate(followup)


# ── Open & Click Tracking ─────────────────────────────────────


@router.get("/email/track/open/{message_id}")
async def track_email_open(message_id: str, db: AsyncSession = Depends(get_db)):
    """Tracking pixel endpoint invoked when a recipient opens an email."""
    await email_service.track_open(db=db, message_id=message_id)
    return Response(content=_TRACKING_PIXEL, media_type="image/gif")


@router.get("/email/track/click/{message_id}")
async def track_email_click(
    message_id: str,
    target: str = "https://github.com",
    db: AsyncSession = Depends(get_db),
):
    """Link click tracking endpoint — records the click and redirects."""
    await email_service.track_click(db=db, message_id=message_id)
    return RedirectResponse(url=target)
