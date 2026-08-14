"""
Ascendra — Users Router.

/me endpoints — profile operations for the authenticated user.
Separate from /auth (per doc §18).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.users.schemas import UpdateProfileRequest, UserResponse
from app.users.service import user_service

router = APIRouter(prefix="/users/me", tags=["Profile"])


@router.get("", response_model=UserResponse)
async def get_profile(user=Depends(get_current_user)):
    """Get the current user's profile."""
    return UserResponse.model_validate(user)


@router.patch("", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    updated = await user_service.update_profile(
        db=db,
        user=user,
        **body.model_dump(exclude_unset=True),
    )
    return UserResponse.model_validate(updated)

@router.delete("")
async def delete_account(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete the current user's account and all associated data."""
    await user_service.delete_account(db=db, user=user)
    return {"success": True, "message": "Account deleted successfully"}
