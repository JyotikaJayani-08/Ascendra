"""
Ascendra — Job & Company Models.

Jobs are normalized from multiple providers into a single internal model.
Companies are shared across users; jobs belong to companies.
"""

import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class RemoteStatus(str, enum.Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    FREELANCE = "FREELANCE"
    UNKNOWN = "UNKNOWN"


class ExperienceLevel(str, enum.Enum):
    ENTRY = "ENTRY"
    MID = "MID"
    SENIOR = "SENIOR"
    LEAD = "LEAD"
    EXECUTIVE = "EXECUTIVE"
    UNKNOWN = "UNKNOWN"


class JobStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class Company(Base):
    """A hiring organization. Shared resource — not user-owned."""
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    jobs: Mapped[list["Job"]] = relationship(back_populates="company")

    def __repr__(self) -> str:
        return f"<Company {self.name}>"


class Job(Base):
    """
    Normalized internal job model.
    Provider-agnostic — the rest of Ascendra never cares where the job came from.
    """
    __tablename__ = "jobs"

    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("companies.id"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_status: Mapped[str] = mapped_column(
        Enum(RemoteStatus, name="remote_status"),
        default=RemoteStatus.UNKNOWN,
    )
    employment_type: Mapped[str] = mapped_column(
        Enum(EmploymentType, name="employment_type"),
        default=EmploymentType.UNKNOWN,
    )
    experience_level: Mapped[str] = mapped_column(
        Enum(ExperienceLevel, name="experience_level"),
        default=ExperienceLevel.UNKNOWN,
    )
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.ACTIVE,
    )

    # Provider tracking
    provider_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    posted_date: Mapped[str | None] = mapped_column(Date, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="jobs")

    def __repr__(self) -> str:
        return f"<Job {self.title} @ {self.company_id[:8]}>"
