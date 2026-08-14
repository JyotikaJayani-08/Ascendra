"""
Ascendra — Resume Models.

Resume = the original uploaded file (immutable).
ResumeVersion = a generated/optimized snapshot (immutable once approved).
Per doc §45: never overwrite resumes.
"""

import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ResumeStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class ResumeVersionStatus(str, enum.Enum):
    GENERATED = "GENERATED"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class ResumeVersionSource(str, enum.Enum):
    ORIGINAL = "ORIGINAL"
    AI_GENERATED = "AI_GENERATED"
    MANUAL = "MANUAL"


class Resume(Base):
    """
    The original uploaded resume. Immutable after upload.
    Binary files stored in Supabase Storage. Metadata stored here.
    """
    __tablename__ = "resumes"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(ResumeStatus, name="resume_status"),
        nullable=False,
        default=ResumeStatus.UPLOADED,
    )
    # Structured resume data extracted by parser (the canonical source of truth)
    structured_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Raw text extracted from PDF
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    versions: Mapped[list["ResumeVersion"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resume {self.original_filename} [{self.status}]>"


class ResumeVersion(Base):
    """
    An optimized/generated version of a resume. Immutable once approved.
    Each version records what prompt and model created it.
    """
    __tablename__ = "resume_versions"

    resume_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resumes.id", ondelete="CASCADE"),
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
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    source: Mapped[str] = mapped_column(
        Enum(ResumeVersionSource, name="resume_version_source"),
        nullable=False,
        default=ResumeVersionSource.ORIGINAL,
    )
    status: Mapped[str] = mapped_column(
        Enum(ResumeVersionStatus, name="resume_version_status"),
        nullable=False,
        default=ResumeVersionStatus.GENERATED,
    )
    # Snapshot of structured data at time of generation (immutable)
    structured_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Generated markdown (UI representation)
    markdown_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Path to generated PDF in Supabase Storage
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Job this version was optimized for (nullable — original has no job)
    job_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    # AI generation metadata
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    label: Mapped[str] = mapped_column(String(255), default="Untitled Version")

    # Relationship
    resume: Mapped["Resume"] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<ResumeVersion v{self.version_number} [{self.status}]>"
