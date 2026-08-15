"""
Ascendra — In-Process Background Scheduler.

Replaces the external pg_cron → pg_net → HTTP chain with a lightweight
asyncio loop that runs inside the FastAPI process itself.

Every 60 seconds it:
  1. Queries for SCHEDULED messages whose scheduled_at <= now
  2. Batch-updates them to QUEUED
  3. Dispatches _send_email_async for each

This works reliably on both localhost and production (Render) without
any external dependencies.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session_factory
from app.email.models import Message, MessageStatus

logger = logging.getLogger("ascendra.scheduler")

SCHEDULER_INTERVAL_SECONDS = 60


async def _process_due_emails() -> int:
    """
    Find all due scheduled emails and dispatch them.

    Returns the number of emails dispatched.
    """
    async with async_session_factory() as db:
        try:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Message).where(
                    Message.status == MessageStatus.SCHEDULED,
                    Message.scheduled_at <= now,
                )
            )
            due_messages = list(result.scalars().all())

            if not due_messages:
                return 0

            # Batch-update statuses
            dispatched_ids = []
            for msg in due_messages:
                msg.status = MessageStatus.QUEUED
                msg.scheduled_at = None
                dispatched_ids.append(str(msg.id))

            await db.commit()

            # Dispatch after commit
            from app.workers.email_tasks import _send_email_async

            for mid in dispatched_ids:
                asyncio.create_task(_send_email_async(mid))

            logger.info(
                f"[Scheduler] Processing {len(dispatched_ids)} due scheduled emails: "
                f"{dispatched_ids}"
            )
            return len(dispatched_ids)

        except Exception as e:
            logger.error(f"[Scheduler] Error processing scheduled emails: {e}")
            await db.rollback()
            return 0


async def _scheduler_loop() -> None:
    """Run the scheduler loop indefinitely."""
    logger.info(
        f"[Scheduler] Started — checking for due emails every "
        f"{SCHEDULER_INTERVAL_SECONDS}s"
    )

    while True:
        try:
            await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)
            await _process_due_emails()
        except asyncio.CancelledError:
            logger.info("[Scheduler] Stopped")
            break
        except Exception as e:
            # Never let an unexpected error kill the scheduler loop
            logger.error(f"[Scheduler] Unexpected error: {e}")
            await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)


def start_email_scheduler() -> asyncio.Task:
    """
    Launch the background scheduler as an asyncio task.

    Returns the task handle so it can be cancelled on shutdown.
    """
    return asyncio.create_task(_scheduler_loop())
