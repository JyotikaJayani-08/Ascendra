"""
Ascendra — Google OAuth Router for Gmail Email Sending.

Handles the OAuth 2.0 authorization code flow to grant the app
permission to send emails via Gmail API on behalf of the user.

Flow:
1. GET /auth/google/authorize → redirect user to Google consent screen
2. GET /auth/google/callback  → exchange code for tokens, save to UserEmailConfig
"""

import logging
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

logger = logging.getLogger("ascendra.auth.google_oauth")

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Scopes required for sending email via Gmail API
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _get_redirect_uri() -> str:
    """Build the OAuth callback URL."""
    return f"{settings.BACKEND_URL}/api/v1/auth/google/callback"


@router.get("/authorize")
async def google_authorize(
    request: Request,
    access_token: str = Query(None, description="Supabase access token passed via query param for browser redirects"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate the Google OAuth consent URL and redirect the user.

    Because this endpoint is triggered via window.location.href (browser redirect),
    we cannot send an Authorization header. Instead, the Supabase access token is
    passed as a ?access_token= query parameter and validated server-side.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    # Resolve user from query param token (browser redirect flow)
    token = access_token or request.headers.get("authorization", "").removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(status_code=401, detail="Access token required.")

    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        user_id = auth_response.user.id
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Google authorize token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _get_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",  # Get refresh_token
        "prompt": "consent",       # Force consent to always get refresh_token
        "state": user_id,
    }

    authorization_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(""),
    error: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback — exchange auth code for tokens and save config.
    
    After success, redirects the user back to the frontend profile page.
    """
    if error:
        logger.warning(f"Google OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/profile?oauth_error={error}"
        )

    if not code:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/profile?oauth_error=no_code"
        )

    user_id = state
    if not user_id:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/profile?oauth_error=invalid_state"
        )

    try:
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": _get_redirect_uri(),
                },
                timeout=15,
            )

        if token_response.status_code != 200:
            logger.error(f"Token exchange failed: {token_response.text}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/dashboard/profile?oauth_error=token_exchange_failed"
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/dashboard/profile?oauth_error=no_access_token"
            )

        # Fetch user's email from Google
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )

        gmail_address = ""
        display_name = ""
        if userinfo_response.status_code == 200:
            userinfo = userinfo_response.json()
            gmail_address = userinfo.get("email", "")
            display_name = userinfo.get("name", "")

        # Save to UserEmailConfig
        from app.auth.email_config_service import email_config_service

        await email_config_service.create_gmail_oauth_config(
            db=db,
            user_id=user_id,
            gmail_address=gmail_address,
            display_name=display_name,
            access_token=access_token,
            refresh_token=refresh_token or "",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

        logger.info(f"Google OAuth connected for user {user_id[:8]} ({gmail_address})")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/profile?oauth_success=true"
        )

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/profile?oauth_error=server_error"
        )
