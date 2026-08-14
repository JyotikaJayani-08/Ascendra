"""
Ascendra — User Email Config Router.

Endpoints for managing per-user SMTP provider connections.
All endpoints are scoped to the authenticated user.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.email_config_schemas import (
    CreateEmailConfigRequest,
    EmailConfigResponse,
    TestEmailConfigRequest,
    TestEmailConfigResponse,
)
from app.auth.email_config_service import email_config_service
from app.core.dependencies import get_current_active_user
from app.database import get_db

router = APIRouter(prefix="/users/me/email-config", tags=["Email Configuration"])


@router.post("", response_model=EmailConfigResponse, status_code=201)
async def save_email_config(
    body: CreateEmailConfigRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Save or update the user's SMTP email configuration."""
    config = await email_config_service.create_config(
        db=db,
        user_id=user.id,
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_username=body.smtp_username,
        smtp_password=body.smtp_password,
        display_name=body.display_name,
        provider_type=body.provider_type,
        oauth_access_token=body.oauth_access_token,
        oauth_refresh_token=body.oauth_refresh_token,
        oauth_client_id=body.oauth_client_id,
        oauth_client_secret=body.oauth_client_secret,
    )
    return _mask_response(config)


@router.get("", response_model=EmailConfigResponse | None)
async def get_email_config(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the user's email configuration (password masked)."""
    config = await email_config_service.get_config(db=db, user_id=user.id)
    if not config:
        return None
    return _mask_response(config)


@router.delete("", status_code=204)
async def delete_email_config(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect the user's email provider."""
    await email_config_service.delete_config(db=db, user_id=user.id)


@router.post("/test", response_model=TestEmailConfigResponse)
async def test_email_config(
    body: TestEmailConfigRequest = TestEmailConfigRequest(),
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test email to verify the user's SMTP configuration."""
    success, message = await email_config_service.test_config(
        db=db,
        user_id=user.id,
        recipient_email=body.recipient_email,
    )
    return TestEmailConfigResponse(success=success, message=message)


def _mask_response(config) -> EmailConfigResponse:
    """Build a response with the password masked."""
    # For OAuth providers, show a different mask since there's no actual password
    password_display = "••••••••"
    if hasattr(config, 'provider_type'):
        provider_str = config.provider_type.value if hasattr(config.provider_type, 'value') else str(config.provider_type)
        if provider_str == "GMAIL_OAUTH":
            password_display = "OAuth Connected"
    
    return EmailConfigResponse(
        id=str(config.id),
        provider_type=config.provider_type.value if hasattr(config.provider_type, 'value') else str(config.provider_type),
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_username=config.smtp_username,
        smtp_password=password_display,
        display_name=config.display_name,
        is_default=config.is_default,
        is_verified=config.is_verified,
        created_at=config.created_at.isoformat() if config.created_at else None,
    )

