"""
Ascendra — Email Schemas.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CreateMessageRequest(BaseModel):
    application_id: str
    to_email: EmailStr
    subject: str = Field(max_length=500)
    body_text: str
    body_html: str | None = None
    scheduled_at: datetime | None = None  # ISO 8601 datetime for scheduled send
    resume_version_id: str | None = None  # Specific resume/version to attach


class ConversationResponse(BaseModel):
    id: str
    application_id: str
    contact_id: str | None = None
    status: str
    subject: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    direction: str
    status: str
    to_email: str
    subject: str
    body_text: str | None = None
    body_html: str | None = None
    ai_generation_id: str | None = None
    send_error: str | None = None
    scheduled_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FollowUpResponse(BaseModel):
    id: str
    conversation_id: str
    status: str
    scheduled_at: datetime
    follow_up_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EditMessageRequest(BaseModel):
    """Request to update a draft/generated email before sending."""
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None


class ScheduleSendRequest(BaseModel):
    """Request to schedule an approved message for future sending."""
    scheduled_at: datetime


class RescheduleRequest(BaseModel):
    """Request to change the scheduled time of a message."""
    scheduled_at: datetime

