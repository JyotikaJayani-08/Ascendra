"""
Ascendra — Notification Service.
"""

import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import Notification, NotificationType

logger = logging.getLogger("ascendra.notifications")


class NotificationService:

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        type: NotificationType,
        title: str,
        message: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Publish to Redis Pub/Sub for real-time SSE delivery
        try:
            from app.core.cache import redis_client
            import json
            if redis_client:
                channel = f"notifications:{user_id}"
                payload = json.dumps({
                    "id": str(notification.id),
                    "type": str(notification.type.value),
                    "title": notification.title,
                    "message": notification.message,
                    "created_at": notification.created_at.isoformat() if notification.created_at else None
                })
                await redis_client.publish(channel, payload)
        except Exception as e:
            logger.error(f"Failed to publish notification to Redis: {e}")

        return notification

    async def list_unread(
        self, db: AsyncSession, user_id: str, limit: int = 50
    ) -> list[Notification]:
        result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(
        self, db: AsyncSession, user_id: str, limit: int = 100
    ) -> list[Notification]:
        result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_read(
        self, db: AsyncSession, notification_id: str, user_id: str
    ) -> None:
        await db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        await db.commit()

    async def mark_all_read(
        self, db: AsyncSession, user_id: str
    ) -> None:
        await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        await db.commit()

    @staticmethod
    async def stream_notifications(user_id: str):
        """
        SSE async generator — yields JSON events from Redis Pub/Sub.

        Falls back to keep-alive pings if Redis is unavailable.
        """
        import asyncio
        import json
        from app.core.cache import redis_client

        if not redis_client:
            while True:
                await asyncio.sleep(15)
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
            return

        try:
            pubsub = redis_client.pubsub()
            channel = f"notifications:{user_id}"
            await pubsub.subscribe(channel)
            try:
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message:
                        yield f"data: {message['data']}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                pass
            finally:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.close()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"SSE Redis PubSub stream fallback active for user {user_id}: {e}")
            while True:
                await asyncio.sleep(15)
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"


notification_service = NotificationService()
