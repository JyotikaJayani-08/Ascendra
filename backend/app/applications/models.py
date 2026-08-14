"""
Ascendra — Application Model.

The Application is the CENTRAL business entity (per doc §23-27).
Everything else — resume versions, emails, conversations, follow-ups,
analytics — revolves around an Application.
"""

import enum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    RESUME_GENERATED = "RESUME_GENERATED"
    EMAIL_GENERATED = "EMAIL_GENERATED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    REPLY_RECEIVED = "REPLY_RECEIVED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    ARCHIVED = "ARCHIVED"


class Application(Base):
    """
    Central business entity. Everything revolves around Applications.
    Connects User → Job → Resume Version → Conversation → Analytics.
    """
    __tablename__ = "applications"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("jobs.id"),
        nullable=False, index=True,
    )
    resume_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_versions.id"),
        nullable=True,
    )
    contact_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        nullable=False,
        default=ApplicationStatus.DRAFT,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Denormalized snapshot (per doc §34 — preserve historical accuracy)
    company_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title_snapshot: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Application {self.id[:8]} [{self.status}]>"

