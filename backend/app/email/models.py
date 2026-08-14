"""
Ascendra — Email Models.

Conversation → Messages → Follow-ups.
Applications own conversations. Conversations own messages.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class MessageStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    EDITED = "EDITED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    REPLIED = "REPLIED"


class MessageDirection(str, enum.Enum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class ConversationStatus(str, enum.Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    REPLIED = "REPLIED"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"


class FollowUpStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    SENT = "SENT"
    CANCELLED = "CANCELLED"


class Conversation(Base):
    """An email thread for one application."""
    __tablename__ = "conversations"

    application_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    contact_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(ConversationStatus, name="conversation_status"),
        default=ConversationStatus.CREATED,
    )
    subject: Mapped[str] = mapped_column(String(500), default="")

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id[:8]} [{self.status}]>"


class Message(Base):
    """A single email in a conversation."""
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    direction: Mapped[str] = mapped_column(
        Enum(MessageDirection, name="message_direction"),
        default=MessageDirection.OUTBOUND,
    )
    status: Mapped[str] = mapped_column(
        Enum(MessageStatus, name="message_status"),
        default=MessageStatus.DRAFT,
    )
    to_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), default="")
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI generation tracking
    ai_generation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    # Provider tracking
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    send_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Scheduled send time (None = send immediately when queued)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # User-selected resume/version to attach
    resume_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id[:8]} [{self.status}] → {self.to_email}>"


class FollowUp(Base):
    """A scheduled follow-up message."""
    __tablename__ = "follow_ups"

    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(FollowUpStatus, name="follow_up_status"),
        default=FollowUpStatus.SCHEDULED,
    )
    scheduled_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    message_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    follow_up_number: Mapped[int] = mapped_column(Integer, default=1)

    def __repr__(self) -> str:
        return f"<FollowUp #{self.follow_up_number} [{self.status}]>"
