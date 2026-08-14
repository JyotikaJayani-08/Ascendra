"""
Ascendra — Notification Models.
"""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class NotificationType(str, enum.Enum):
    RESUME_PARSED = "RESUME_PARSED"
    RESUME_GENERATED = "RESUME_GENERATED"
    EMAIL_SENT = "EMAIL_SENT"
    EMAIL_FAILED = "EMAIL_FAILED"
    REPLY_RECEIVED = "REPLY_RECEIVED"
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE"
    APPLICATION_STATUS = "APPLICATION_STATUS"
    SYSTEM = "SYSTEM"


class Notification(Base):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    type: Mapped[str] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    def __repr__(self) -> str:
        return f"<Notification {self.type} read={self.is_read}>"
