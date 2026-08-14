"""
Ascendra — Resume Schemas.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ResumeResponse(BaseModel):
    id: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    status: str
    structured_data: dict | None = None
    raw_text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeVersionResponse(BaseModel):
    id: str
    resume_id: str
    version_number: int
    parent_version_id: str | None = None
    source: str
    status: str
    structured_data: dict | None = None
    markdown_content: str | None = None
    pdf_path: str | None = None
    job_id: str | None = None
    prompt_version: str | None = None
    model_used: str | None = None
    label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateResumeVersionRequest(BaseModel):
    resume_id: str
    job_id: str | None = None
    label: str = Field(default="AI Optimized", max_length=255)


class ApproveVersionRequest(BaseModel):
    pass  # Just needs the version_id from URL


class BulkDeleteRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


class BulkDeleteResponse(BaseModel):
    deleted_count: int
    message: str


class SiblingVersionItem(BaseModel):
    id: str
    version_number: int
    label: str
    created_at: str


class ResumeCompareResponse(BaseModel):
    version_id: str
    resume_id: str
    original_filename: str
    version_label: str
    version_number: int
    original_ats_score: int = 0
    ats_score: int | None = None
    score_improvement: int = 0
    ats_feedback: str | None = None
    original_skills: list[str] = []
    matched_keywords: list[str] = []
    missing_skills: list[str] = []
    added_keywords: list[str] = []
    original_text_snippet: str | None = None
    tailored_markdown: str | None = None
    sibling_versions: list[SiblingVersionItem] = []
    created_at: datetime

    model_config = {"from_attributes": True}
