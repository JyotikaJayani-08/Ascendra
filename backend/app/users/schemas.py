"""
Ascendra — User Profile Schemas.

Separate from Auth schemas — profile is about "what" a user is,
auth is about "who" a user is.
"""

from pydantic import BaseModel, Field, field_validator


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=20)
    location: str | None = Field(None, max_length=255)
    linkedin_url: str | None = Field(None)
    github_url: str | None = Field(None)
    portfolio_url: str | None = Field(None)
    bio: str | None = Field(None, max_length=2000)

    @field_validator("linkedin_url", "github_url", "portfolio_url", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty strings to None so Pydantic doesn't reject them."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def empty_phone_to_none(cls, v):
        """Convert empty phone strings to None."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    status: str
    email_verified: bool
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    bio: str | None = None

    class Config:
        from_attributes = True
