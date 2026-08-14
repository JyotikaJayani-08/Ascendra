"""
Ascendra — AI Schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GenerateResumeRequest(BaseModel):
    resume_id: str
    job_id: str | None = None
    label: str = Field(default="AI Optimized", max_length=255)
    tailoring_style: str = Field(
        default="ats_optimized",
        description="Tailoring approach: ats_optimized, narrative, skills_focused, experience_focused",
    )
    focus_keywords: list[str] | None = Field(
        default=None,
        description="Priority keywords to emphasize in the tailored resume",
    )
    custom_instructions: str | None = Field(
        default=None,
        max_length=1000,
        description="Free-text instructions for the AI (e.g. 'emphasize leadership experience')",
    )


class GenerateEmailRequest(BaseModel):
    application_id: str
    tone: str = Field(default="professional", max_length=50)


class GenerateFollowUpRequest(BaseModel):
    conversation_id: str
    follow_up_number: int = Field(default=1, ge=1, le=5)
    tone: str = Field(default="professional", max_length=50)


class AIGenerationResponse(BaseModel):
    id: str
    generation_type: str
    model_used: str
    prompt_version: str
    total_tokens: int
    entity_type: str | None = None
    entity_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
