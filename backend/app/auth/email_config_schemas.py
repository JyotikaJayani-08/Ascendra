"""
Ascendra — User Email Config Schemas.

Request/response models for per-user SMTP provider configuration.
Password is always masked in responses — never returned to the frontend.
"""

from pydantic import BaseModel, Field, field_validator


class CreateEmailConfigRequest(BaseModel):
    """Request to save a user's SMTP or OAuth email configuration."""
    provider_type: str = Field(default="SMTP", description="Provider type: SMTP, GMAIL_OAUTH, OUTLOOK_OAUTH")
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server hostname")
    smtp_port: int = Field(default=587, ge=0, le=65535, description="SMTP server port")
    smtp_username: str = Field(
        ...,
        min_length=3,
        max_length=320,
        pattern=r"^[^@]+@[^@]+\.[^@]+$",
        description="SMTP login email",
    )
    smtp_password: str = Field(default="", max_length=512, description="SMTP password or App Password (optional for OAuth)")
    display_name: str | None = Field(None, max_length=255, description="Display name for From header")
    
    oauth_access_token: str | None = Field(None, description="OAuth access token")
    oauth_refresh_token: str | None = Field(None, description="OAuth refresh token")
    oauth_client_id: str | None = Field(None, description="OAuth Client ID")
    oauth_client_secret: str | None = Field(None, description="OAuth Client Secret")

    model_config = {"extra": "forbid"}


class UpdateEmailConfigRequest(BaseModel):
    """Request to update an existing email configuration."""
    provider_type: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = Field(None, ge=1, le=65535)
    smtp_username: str | None = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    smtp_password: str | None = None
    display_name: str | None = None
    
    oauth_access_token: str | None = None
    oauth_refresh_token: str | None = None
    oauth_client_id: str | None = None
    oauth_client_secret: str | None = None

    model_config = {"extra": "forbid"}


class EmailConfigResponse(BaseModel):
    """Response with email config — password and tokens are always masked."""
    id: str
    provider_type: str = "SMTP"
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str = "••••••••"  # Never expose real password
    display_name: str | None = None
    is_default: bool = True
    is_verified: bool = False
    created_at: str | None = None

    model_config = {"from_attributes": True}


class TestEmailConfigRequest(BaseModel):
    """Request to send a test email to verify SMTP configuration."""
    recipient_email: str | None = Field(
        None, description="Email to send test to. Defaults to the SMTP username."
    )

    model_config = {"extra": "forbid"}


class TestEmailConfigResponse(BaseModel):
    """Result of the SMTP test."""
    success: bool
    message: str
