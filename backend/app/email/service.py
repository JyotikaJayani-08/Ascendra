"""
Ascendra — Email Service.

Conversation management, message lifecycle, approval flow.
Sending is always async (queued) — never from an HTTP request.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateTransition, NotFound, PermissionDenied
from app.email.models import (
    Conversation,
    ConversationStatus,
    FollowUp,
    Message,
    MessageDirection,
    MessageStatus,
)

logger = logging.getLogger("ascendra.email")


class EmailService:

    async def create_draft(
        self,
        db: AsyncSession,
        user_id: str,
        application_id: str,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        contact_id: str | None = None,
        ai_generation_id: str | None = None,
        resume_version_id: str | None = None,
    ) -> tuple[Conversation, Message]:
        """Create a conversation + draft message for an application."""
        # Find or create conversation
        result = await db.execute(
            select(Conversation).where(
                Conversation.application_id == application_id,
                Conversation.user_id == user_id,
                Conversation.status != ConversationStatus.ARCHIVED,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                application_id=application_id,
                user_id=user_id,
                contact_id=contact_id,
                status=ConversationStatus.CREATED,
                subject=subject,
            )
            db.add(conversation)
            await db.flush()

        # Ensure body content is never empty
        if not body_text and not body_html:
            from app.core.exceptions import ValidationError
            raise ValidationError("Email body cannot be empty.")

        clean_text = body_text or (body_html.replace("<p>", "").replace("</p>", "").replace("<br>", "\n") if body_html else "")
        clean_html = body_html or f"<p>{clean_text}</p>"

        # Create message
        message = Message(
            conversation_id=conversation.id,
            user_id=user_id,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.DRAFT,
            to_email=to_email,
            subject=subject,
            body_text=clean_text,
            body_html=clean_html,
            ai_generation_id=ai_generation_id,
            resume_version_id=resume_version_id,
        )
        db.add(message)
        await db.commit()
        await db.refresh(conversation)
        await db.refresh(message)

        logger.info(f"Draft created: {message.id[:8]} → {to_email}")
        return conversation, message

    async def approve_message(
        self,
        db: AsyncSession,
        message_id: str,
        user_id: str,
    ) -> Message:
        """Approve a draft message for sending."""
        message = await self._get_message(db, message_id, user_id)

        if message.status not in (MessageStatus.DRAFT, MessageStatus.GENERATED, MessageStatus.EDITED):
            raise InvalidStateTransition(message.status, MessageStatus.APPROVED)

        message.status = MessageStatus.APPROVED
        await db.commit()

        logger.info(f"Message approved: {message_id[:8]}")
        return message

    async def queue_message(
        self,
        db: AsyncSession,
        message_id: str,
        user_id: str,
    ) -> Message:
        """Queue an approved message for sending."""
        message = await self._get_message(db, message_id, user_id)

        if message.status != MessageStatus.APPROVED:
            raise InvalidStateTransition(message.status, MessageStatus.QUEUED)

        message.status = MessageStatus.QUEUED
        await db.commit()

        logger.info(f"Message queued: {message_id[:8]}")
        return message

    async def schedule_message(
        self,
        db: AsyncSession,
        message_id: str,
        user_id: str,
        scheduled_at: "datetime",
    ) -> Message:
        """Schedule an approved message for future sending."""
        from datetime import datetime, timezone

        message = await self._get_message(db, message_id, user_id)

        if message.status not in (MessageStatus.APPROVED, MessageStatus.SCHEDULED):
            raise InvalidStateTransition(message.status, MessageStatus.SCHEDULED)

        # Ensure scheduled_at is timezone-aware (treat naive as UTC)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        logger.info(
            f"Schedule check: scheduled_at={scheduled_at.isoformat()} "
            f"now_utc={now_utc.isoformat()} "
            f"is_past={scheduled_at <= now_utc}"
        )

        if scheduled_at <= now_utc:
            # If scheduled time is in the past or now, queue immediately
            message.status = MessageStatus.QUEUED
            message.scheduled_at = None
            await db.commit()
            logger.info(f"Message {message_id[:8]} scheduled in past, queuing immediately")
            return message

        message.status = MessageStatus.SCHEDULED
        message.scheduled_at = scheduled_at
        await db.commit()

        logger.info(f"Message scheduled: {message_id[:8]} at {scheduled_at.isoformat()}")
        return message

    async def reschedule_message(
        self,
        db: AsyncSession,
        message_id: str,
        user_id: str,
        scheduled_at: "datetime",
    ) -> Message:
        """Reschedule a scheduled message to a new time."""
        from datetime import datetime, timezone

        message = await self._get_message(db, message_id, user_id)

        if message.status != MessageStatus.SCHEDULED:
            raise InvalidStateTransition(message.status, MessageStatus.SCHEDULED)

        # Ensure scheduled_at is timezone-aware (treat naive as UTC)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        logger.info(
            f"Reschedule check: scheduled_at={scheduled_at.isoformat()} "
            f"now_utc={now_utc.isoformat()} "
            f"is_past={scheduled_at <= now_utc}"
        )

        if scheduled_at <= now_utc:
            message.status = MessageStatus.QUEUED
            message.scheduled_at = None
            await db.commit()
            logger.info(f"Reschedule to past — message {message_id[:8]} queued immediately")
            return message

        message.scheduled_at = scheduled_at
        await db.commit()

        logger.info(f"Message rescheduled: {message_id[:8]} to {scheduled_at.isoformat()}")
        return message

    async def cancel_scheduled(
        self,
        db: AsyncSession,
        message_id: str,
        user_id: str,
    ) -> Message:
        """Cancel a scheduled message, returning it to APPROVED status."""
        message = await self._get_message(db, message_id, user_id)

        if message.status != MessageStatus.SCHEDULED:
            raise InvalidStateTransition(message.status, MessageStatus.APPROVED)

        message.status = MessageStatus.APPROVED
        message.scheduled_at = None
        await db.commit()

        logger.info(f"Scheduled message cancelled: {message_id[:8]}")
        return message

    async def get_due_scheduled(self, db: AsyncSession) -> list[Message]:
        """Get all messages that are due for sending (scheduled_at <= now).

        Called by the Supabase Edge Function via pg_cron.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Message).where(
                Message.status == MessageStatus.SCHEDULED,
                Message.scheduled_at <= now,
            )
        )
        return list(result.scalars().all())

    async def edit_message(
        self,
        db: AsyncSession,
        message_id: str,
        user_id: str,
        subject: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
    ) -> Message:
        """Edit a draft/generated message before sending."""
        message = await self._get_message(db, message_id, user_id)

        if message.status not in (MessageStatus.DRAFT, MessageStatus.GENERATED, MessageStatus.EDITED):
            raise InvalidStateTransition(message.status, MessageStatus.EDITED)

        if subject is not None:
            message.subject = subject
        if body_text is not None:
            message.body_text = body_text
            if body_html is None:
                # Auto-generate HTML from text if no explicit HTML provided
                message.body_html = "<p>" + body_text.replace("\n\n", "</p><p>").replace("\n", "<br/>") + "</p>"
        if body_html is not None:
            message.body_html = body_html

        message.status = MessageStatus.EDITED
        await db.commit()

        logger.info(f"Message edited: {message_id[:8]}")
        return message

    async def mark_sent(
        self,
        db: AsyncSession,
        message_id: str,
        provider_message_id: str | None = None,
    ) -> Message:
        """Mark a message as sent (called by worker after successful send)."""
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            raise NotFound("Message")

        message.status = MessageStatus.SENT
        message.provider_message_id = provider_message_id

        # Update conversation status & linked application status
        result = await db.execute(
            select(Conversation).where(Conversation.id == message.conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.status = ConversationStatus.WAITING
            if conversation.application_id:
                from app.applications.models import Application
                app_res = await db.execute(
                    select(Application).where(Application.id == conversation.application_id)
                )
                app_obj = app_res.scalar_one_or_none()
                if app_obj:
                    app_obj.status = "SENT"

        await db.commit()
        return message

    async def mark_failed(
        self, db: AsyncSession, message_id: str, error: str
    ) -> Message:
        """Mark a message as failed."""
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            raise NotFound("Message")

        message.status = MessageStatus.FAILED
        message.send_error = error
        await db.commit()
        return message

    async def get_conversations(
        self, db: AsyncSession, user_id: str
    ) -> list[Conversation]:
        """List all conversations for a user."""
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_conversation_messages(
        self, db: AsyncSession, conversation_id: str, user_id: str
    ) -> list[Message]:
        """Get all messages in a conversation."""
        # Verify ownership
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if not result.scalar_one_or_none():
            raise NotFound("Conversation")

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_stats(self, db: AsyncSession, user_id: str) -> dict[str, int]:
        """Get email stats for dashboard."""
        convo_count_result = await db.execute(
            select(func.count()).select_from(Conversation).where(
                Conversation.user_id == user_id
            )
        )
        total_convos = convo_count_result.scalar() or 0

        sent_count_result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.user_id == user_id,
                Message.status == MessageStatus.SENT,
            )
        )
        total_sent = sent_count_result.scalar() or 0
        
        return {
            "total_conversations": total_convos,
            "total_messages_sent": total_sent
        }

    async def track_open(self, db: AsyncSession, message_id: str) -> None:
        """Record that a recipient opened the email (tracking pixel hit)."""
        import uuid
        try:
            uuid.UUID(message_id)
        except Exception:
            logger.info(f"Tracking: email opened ping with test/mock ID [{message_id}]")
            return

        try:
            result = await db.execute(
                select(Message).where(Message.id == message_id)
            )
            msg = result.scalar_one_or_none()
            if msg and msg.status == MessageStatus.SENT:
                msg.status = MessageStatus.DELIVERED
                await db.commit()
                logger.info(f"Tracking: email opened [{message_id[:8]}]")
        except Exception as err:
            logger.warning(f"Tracking open error for {message_id}: {err}")

    async def track_click(self, db: AsyncSession, message_id: str) -> None:
        """Record that a recipient clicked a link in the email."""
        import uuid
        try:
            uuid.UUID(message_id)
        except Exception:
            logger.info(f"Tracking: link click ping with test/mock ID [{message_id}]")
            return

        try:
            result = await db.execute(
                select(Message).where(Message.id == message_id)
            )
            msg = result.scalar_one_or_none()
            if msg and msg.status in (MessageStatus.SENT, MessageStatus.DELIVERED):
                msg.status = MessageStatus.DELIVERED
                await db.commit()
                logger.info(f"Tracking: link clicked [{message_id[:8]}]")
        except Exception as err:
            logger.warning(f"Tracking click error for {message_id}: {err}")

    async def _get_message(
        self, db: AsyncSession, message_id: str, user_id: str
    ) -> Message:
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            raise NotFound("Message")
        if message.user_id != user_id:
            raise PermissionDenied()
        return message


email_service = EmailService()
