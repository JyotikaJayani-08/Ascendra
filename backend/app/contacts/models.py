"""
Ascendra — Contact Models.

Contacts are hiring recruiters/managers discovered for companies.
Confidence-scored, not assumed to be correct.
"""

import enum

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ContactSource(str, enum.Enum):
    MANUAL = "MANUAL"
    SCRAPED = "SCRAPED"
    DISCOVERED = "DISCOVERED"
    HUNTER = "HUNTER"
    APOLLO = "APOLLO"
    ROCKETREACH = "ROCKETREACH"
    OTHER = "OTHER"


class VerificationStatus(str, enum.Enum):
    UNKNOWN = "UNKNOWN"
    UNVERIFIED = "UNVERIFIED"
    ESTIMATED = "ESTIMATED"
    VERIFIED = "VERIFIED"
    INVALID = "INVALID"


class Contact(Base):
    __tablename__ = "contacts"

    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("companies.id"),
        nullable=False, index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(
        Enum(ContactSource, name="contact_source"),
        default=ContactSource.MANUAL,
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    verification_status: Mapped[str] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        default=VerificationStatus.UNKNOWN,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Who added this — null for system-discovered
    added_by_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    def __repr__(self) -> str:
        return f"<Contact {self.full_name} ({self.confidence_score:.0%})>"
