"""
Ascendra — FastAPI Dependencies.

Reusable dependencies injected into route handlers.
"""

import logging

import jwt as pyjwt
from jwt.exceptions import PyJWTError
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import TokenInvalid
from app.database import get_db

logger = logging.getLogger("ascendra.auth")

security_scheme = HTTPBearer()


def _decode_supabase_jwt(token: str) -> dict:
    """
    Decode a Supabase JWT locally using the shared JWT_SECRET.

    This avoids a ~2-second network roundtrip to Supabase Auth on every
    request.  The token already contains the user's ID (``sub``), email,
    and metadata — all cryptographically signed with the same secret that
    Supabase and this backend share.
    """
    return pyjwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        audience="authenticated",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and validate the current user from the Bearer token.

    Primary path: decode the Supabase JWT locally (~0.1 ms).
    Fallback path: call Supabase Auth API if local decode fails
    (e.g. key rotation, token format change).
    """
    from app.auth.models import User

    token = credentials.credentials

    # ── Step 1: Verify the token ──────────────────────────────
    user_id: str | None = None
    email: str | None = None
    full_name: str = ""

    try:
        payload = _decode_supabase_jwt(token)
        user_id = payload.get("sub")
        email = payload.get("email")
        user_metadata = payload.get("user_metadata") or {}
        full_name = user_metadata.get("full_name", "")
    except (PyJWTError, Exception) as e:
        logger.debug(f"Local JWT decode failed, falling back to Supabase API: {e}")
        try:
            from supabase import create_client, Client

            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            auth_response = supabase.auth.get_user(token)
            if not auth_response or not auth_response.user:
                raise TokenInvalid()

            user_id = auth_response.user.id
            email = auth_response.user.email
            user_metadata = auth_response.user.user_metadata or {}
            full_name = user_metadata.get("full_name", "")
        except TokenInvalid:
            raise
        except Exception:
            raise TokenInvalid()

    if not user_id or not email:
        raise TokenInvalid()

    # ── Step 2: Look up user in local DB ──────────────────────
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Check for a stale row with the same email but a different PK
        # (happens when a Supabase account is deleted and re-created).
        email_result = await db.execute(select(User).where(User.email == email))
        stale_user = email_result.scalar_one_or_none()

        if stale_user:
            # Fix 3: UPDATE the primary key in-place so all FK references
            # (resumes, messages, conversations, etc.) stay intact.
            logger.info(
                f"Migrating user ID for {email}: {stale_user.id} → {user_id}"
            )
            try:
                await db.execute(
                    update(User)
                    .where(User.id == stale_user.id)
                    .values(id=user_id)
                )
                await db.commit()
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
            except Exception as migrate_err:
                await db.rollback()
                logger.warning(f"User ID migration failed: {migrate_err}")
                # Use the existing record as-is rather than crashing
                user = stale_user
        else:
            # Genuinely new user — lazy-create
            user = User(
                id=user_id,
                email=email,
                full_name=full_name,
                email_verified=True,
            )
            db.add(user)
            try:
                await db.commit()
                await db.refresh(user)
            except Exception as insert_err:
                await db.rollback()
                # Another concurrent request may have inserted first
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if not user:
                    logger.error(f"Failed to initialize user {user_id}: {insert_err}")
                    from fastapi import HTTPException

                    raise HTTPException(
                        status_code=500,
                        detail="Failed to initialize user profile.",
                    )

    if user.status == "SUSPENDED":
        from app.core.exceptions import AccountSuspended

        raise AccountSuspended()

    return user


async def get_current_active_user(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ensures the user is in an active state and resolves active workspace context."""
    if user.status not in ("ACTIVE", "PROFILE_INCOMPLETE"):
        from app.core.exceptions import EmailNotVerified
        raise EmailNotVerified()
    
    # Resolve Workspace Context
    # Check if frontend sent a specific workspace header
    workspace_id = request.headers.get("x-workspace-id")
    
    if workspace_id:
        # Validate that the user is actually a member of this workspace
        from app.workspaces.models import WorkspaceMember
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.workspace_id == workspace_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        user.active_workspace_id = workspace_id
        user.workspace_role = member.role
    else:
        # Default to their first workspace if they have one
        from app.workspaces.models import WorkspaceMember
        result = await db.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user.id).limit(1)
        )
        member = result.scalar_one_or_none()
        if member:
            user.active_workspace_id = member.workspace_id
            user.workspace_role = member.role
        else:
            user.active_workspace_id = None
            user.workspace_role = None

    return user


async def get_user_from_query_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user via a query-string token.

    Used by SSE/WebSocket endpoints where the browser cannot send
    Authorization headers (e.g., EventSource).

    Fix 2: The User object is refreshed within the async session so that
    accessing ``user.id`` later (in the SSE generator) does not trigger a
    lazy-load outside the greenlet context.
    """
    from app.auth.models import User

    # ── Verify the token ──────────────────────────────────────
    user_id: str | None = None
    email: str | None = None

    try:
        payload = _decode_supabase_jwt(token)
        user_id = payload.get("sub")
        email = payload.get("email")
    except (PyJWTError, Exception) as e:
        logger.debug(f"SSE local JWT decode failed, falling back to Supabase API: {e}")
        try:
            from supabase import create_client, Client

            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            auth_response = supabase.auth.get_user(token)
            if not auth_response or not auth_response.user:
                raise TokenInvalid()

            user_id = auth_response.user.id
            email = auth_response.user.email
        except TokenInvalid:
            raise
        except Exception:
            raise TokenInvalid()

    if not user_id:
        raise TokenInvalid()

    # ── Look up user ──────────────────────────────────────────
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user and email:
        # Migrate stale user record (same logic as get_current_user)
        email_result = await db.execute(select(User).where(User.email == email))
        stale_user = email_result.scalar_one_or_none()

        if stale_user:
            try:
                await db.execute(
                    update(User)
                    .where(User.id == stale_user.id)
                    .values(id=user_id)
                )
                await db.commit()
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
            except Exception:
                await db.rollback()
                user = stale_user

    if not user:
        raise TokenInvalid()

    # Fix 2: Eagerly materialise the user's scalar attributes so the SSE
    # generator can read ``user.id`` without triggering a lazy-load
    # outside the async greenlet context.
    _ = user.id
    _ = user.email

    return user

