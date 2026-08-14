"""
Ascendra — Contact Schemas.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class ContactResponse(BaseModel):
    id: str
    company_id: str
    full_name: str
    job_title: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    source: str
    confidence_score: float
    verification_status: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    items: list[ContactResponse]
    total: int
    page: int
    page_size: int


class CreateContactRequest(BaseModel):
    company_id: str
    full_name: str = Field(max_length=255)
    job_title: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    linkedin_url: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=2000)


class UpdateContactRequest(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    job_title: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    linkedin_url: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=2000)
