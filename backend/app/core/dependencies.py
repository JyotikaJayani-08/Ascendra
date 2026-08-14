"""
Ascendra — FastAPI Dependencies.

Reusable dependencies injected into route handlers.
"""

import logging

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import TokenInvalid
from app.database import get_db

logger = logging.getLogger("ascendra.auth")

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and validate the current user from the Bearer token.
    Supabase GoTrue JWT is verified here using the JWT_SECRET.
    Lazily creates the user record if it doesn't exist.
    """
    from app.auth.models import User
    from supabase import create_client, Client
    from sqlalchemy import update
    
    try:
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        auth_response = supabase.auth.get_user(credentials.credentials)
        if not auth_response or not auth_response.user:
            raise TokenInvalid()
            
        user_id = auth_response.user.id
        email = auth_response.user.email
    except TokenInvalid:
        raise
    except Exception as e:
        logger.warning(f"Supabase token validation failed: {e}")
        raise TokenInvalid()

    if not user_id or not email:
        raise TokenInvalid()

    # Query user by Supabase ID
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Check if a stale row exists in local DB with this email (e.g. from an old deleted account)
        email_result = await db.execute(select(User).where(User.email == email))
        stale_user = email_result.scalar_one_or_none()

        if stale_user:
            logger.info(f"Cleaning up stale user record for email {email} (Old ID: {stale_user.id})")
            await db.delete(stale_user)
            await db.commit()

        # Lazy creation: User authenticated via Supabase but doesn't exist in our public schema yet
        user_metadata = auth_response.user.user_metadata or {}
        full_name = user_metadata.get("full_name", "")
        
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
            # Re-fetch if inserted concurrently by another request
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                logger.error(f"Failed to initialize user {user_id}: {insert_err}")
                from fastapi import HTTPException
                raise HTTPException(status_code=500, detail="Failed to initialize user profile.")

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
    """
    from app.auth.models import User
    from supabase import create_client, Client
    from sqlalchemy import update

    try:
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
            raise TokenInvalid()

        user_id = auth_response.user.id
        email = auth_response.user.email

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user and email:
            email_result = await db.execute(select(User).where(User.email == email))
            user_by_email = email_result.scalar_one_or_none()
            if user_by_email:
                old_id = user_by_email.id
                try:
                    await db.execute(
                        update(User)
                        .where(User.id == old_id)
                        .values(id=user_id)
                    )
                    await db.commit()
                    result = await db.execute(select(User).where(User.id == user_id))
                    user = result.scalar_one_or_none()
                except Exception:
                    await db.rollback()
                    user = user_by_email

        if not user:
            raise TokenInvalid()
        return user
    except TokenInvalid:
        raise
    except Exception:
        raise TokenInvalid()

