"""
Ascendra — Users Service.

Profile updates and status management.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserStatus
from app.config import settings

logger = logging.getLogger("ascendra.users")


class UserService:
    async def update_profile(
        self,
        db: AsyncSession,
        user: User,
        full_name: str | None = None,
        phone: str | None = None,
        location: str | None = None,
        linkedin_url: str | None = None,
        github_url: str | None = None,
        portfolio_url: str | None = None,
        bio: str | None = None,
    ) -> User:
        """Update user profile fields. Transitions to ACTIVE if profile is complete."""
        if full_name is not None:
            user.full_name = full_name
        if phone is not None:
            user.phone = phone
        if location is not None:
            user.location = location
        if linkedin_url is not None:
            user.linkedin_url = linkedin_url
        if github_url is not None:
            user.github_url = github_url
        if portfolio_url is not None:
            user.portfolio_url = portfolio_url
        if bio is not None:
            user.bio = bio

        # Transition to ACTIVE if profile is sufficiently filled
        if user.status == UserStatus.PROFILE_INCOMPLETE:
            if user.full_name and user.location:
                user.status = UserStatus.ACTIVE

        await db.commit()
        await db.refresh(user)

        logger.info(f"Profile updated: {user.email}")
        return user

    async def get_profile(self, user: User) -> User:
        """Return the user object (already loaded by dependency)."""
        return user

    async def delete_account(self, db: AsyncSession, user: User) -> None:
        """
        Delete the user account permanently:
        1. Hard-delete from local DB (cascades to all child tables)
        2. Delete from Supabase Auth so they cannot re-login
        """
        user_id = user.id
        user_email = user.email

        # Step 1: Hard-delete in local DB (PostgreSQL handles cascading via ondelete='CASCADE')
        await db.delete(user)
        await db.commit()
        logger.info(f"Account permanently deleted from local DB: {user_email}")

        # Step 2: Delete from Supabase Auth (requires service_role key)
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            supabase.auth.admin.delete_user(user_id)
            logger.info(f"Account deleted from Supabase Auth: {user_email}")
        except Exception as e:
            logger.error(f"Failed to delete from Supabase Auth: {e}")



user_service = UserService()
