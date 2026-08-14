"""
Ascendra — Application Schemas.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateApplicationRequest(BaseModel):
    job_id: str
    resume_version_id: str | None = None
    contact_id: str | None = None
    notes: str | None = Field(None, max_length=5000)

    model_config = {"extra": "forbid"}


class UpdateApplicationRequest(BaseModel):
    resume_version_id: str | None = None
    contact_id: str | None = None
    notes: str | None = Field(None, max_length=5000)

    model_config = {"extra": "forbid"}


class TransitionApplicationRequest(BaseModel):
    target_status: str

    model_config = {"extra": "forbid"}


class ApplicationResponse(BaseModel):
    id: str
    user_id: str
    job_id: str
    resume_version_id: str | None = None
    contact_id: str | None = None
    status: str
    notes: str | None = None
    company_name_snapshot: str | None = None
    job_title_snapshot: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    items: list[ApplicationResponse]
    total: int
    page: int
    page_size: int
