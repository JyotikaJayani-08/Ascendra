"""
Ascendra — Auth Router.

Cookie management & Token Rotation for Refresh Tokens (HTTP-only).
"""

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.cache import blacklist_token, is_token_blacklisted
from app.core.limiter import limiter
import time
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

COOKIE_NAME = "refresh_token"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set secure HTTP-only cookie for refresh token."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth",
    )


@router.post("/cookie/set")
@limiter.limit("10/minute")
async def set_cookie_endpoint(request: Request, response: Response):
    """
    Store refresh token in HTTP-only cookie.
    Client sends the refresh token in request payload or header once upon auth.
    """
    data = await request.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token required")

    set_refresh_cookie(response, refresh_token)
    return {"success": True, "message": "Secure HTTP-only cookie set"}


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh_tokens(request: Request, response: Response):
    """
    Rotate Refresh Token & issue new Access Token using HTTP-only cookie.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token cookie missing")

    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            response.delete_cookie(key=COOKIE_NAME, path="/auth")
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        user_id = payload.get("sub")
        session_id = payload.get("sid", "default_session")

        # Issue new token pair (Rotation)
        new_access_token = create_access_token(user_id=user_id)
        new_refresh_token = create_refresh_token(user_id=user_id, session_id=session_id)

        # Set new cookie
        set_refresh_cookie(response, new_refresh_token)

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except Exception:
        response.delete_cookie(key=COOKIE_NAME, path="/auth")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(request: Request, response: Response):
    """Clear the HTTP-only refresh token cookie and blacklist it."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                ttl = max(0, int(exp - time.time()))
                if ttl > 0:
                    await blacklist_token(jti, ttl)
        except Exception:
            pass  # Token invalid anyway

    response.delete_cookie(key=COOKIE_NAME, path="/auth")
    return {"success": True, "message": "Logged out successfully"}
