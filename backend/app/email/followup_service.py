"""
Ascendra — Follow-up Service.

Schedule, list, and cancel follow-up emails.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFound, PermissionDenied, ValidationError
from app.email.models import (
    Conversation,
    FollowUp,
    FollowUpStatus,
    Message,
    MessageStatus,
)

logger = logging.getLogger("ascendra.followups")


class FollowUpService:

    async def schedule(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str,
        days_after: int = 3,
        follow_up_number: int | None = None,
    ) -> FollowUp:
        """Schedule a follow-up email for a conversation."""
        # Validate conversation ownership
        conv = await self._get_conversation(db, conversation_id, user_id)

        if days_after < 1 or days_after > 30:
            raise ValidationError("Follow-up must be scheduled between 1 and 30 days from now.")

        # Auto-determine follow-up number
        if follow_up_number is None:
            result = await db.execute(
                select(FollowUp).where(
                    FollowUp.conversation_id == conversation_id,
                    FollowUp.user_id == user_id,
                )
            )
            existing = list(result.scalars().all())
            follow_up_number = len(existing) + 1

        scheduled_at = datetime.now(timezone.utc) + timedelta(days=days_after)

        followup = FollowUp(
            conversation_id=conversation_id,
            user_id=user_id,
            status=FollowUpStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            follow_up_number=follow_up_number,
        )
        db.add(followup)
        await db.commit()
        await db.refresh(followup)

        logger.info(
            f"Follow-up #{follow_up_number} scheduled for conversation "
            f"{conversation_id[:8]} at {scheduled_at.isoformat()}"
        )
        return followup

    async def get_pending(
        self, db: AsyncSession, user_id: str
    ) -> list[FollowUp]:
        """Get all pending follow-ups for a user."""
        result = await db.execute(
            select(FollowUp)
            .where(
                FollowUp.user_id == user_id,
                FollowUp.status == FollowUpStatus.SCHEDULED,
            )
            .order_by(FollowUp.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_conversation(
        self, db: AsyncSession, conversation_id: str, user_id: str
    ) -> list[FollowUp]:
        """Get all follow-ups for a specific conversation."""
        result = await db.execute(
            select(FollowUp)
            .where(
                FollowUp.conversation_id == conversation_id,
                FollowUp.user_id == user_id,
            )
            .order_by(FollowUp.follow_up_number.asc())
        )
        return list(result.scalars().all())

    async def cancel(
        self, db: AsyncSession, followup_id: str, user_id: str
    ) -> FollowUp:
        """Cancel a scheduled follow-up."""
        result = await db.execute(
            select(FollowUp).where(FollowUp.id == followup_id)
        )
        followup = result.scalar_one_or_none()
        if not followup:
            raise NotFound("FollowUp")
        if followup.user_id != user_id:
            raise PermissionDenied()
        if followup.status != FollowUpStatus.SCHEDULED:
            raise ValidationError("Only scheduled follow-ups can be cancelled.")

        followup.status = FollowUpStatus.CANCELLED
        await db.commit()

        logger.info(f"Follow-up {followup_id[:8]} cancelled")
        return followup

    async def get_due_followups(self, db: AsyncSession) -> list[FollowUp]:
        """Get all follow-ups that are due for sending (past scheduled_at)."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(FollowUp).where(
                FollowUp.status == FollowUpStatus.SCHEDULED,
                FollowUp.scheduled_at <= now,
            )
        )
        return list(result.scalars().all())

    async def mark_sent(
        self, db: AsyncSession, followup_id: str, message_id: str
    ) -> None:
        """Mark a follow-up as sent after the email was dispatched."""
        await db.execute(
            update(FollowUp)
            .where(FollowUp.id == followup_id)
            .values(status=FollowUpStatus.SENT, message_id=message_id)
        )
        await db.commit()

    async def _get_conversation(
        self, db: AsyncSession, conversation_id: str, user_id: str
    ) -> Conversation:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise NotFound("Conversation")
        if conv.user_id != user_id:
            raise PermissionDenied()
        return conv


followup_service = FollowUpService()
