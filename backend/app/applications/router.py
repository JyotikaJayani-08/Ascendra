"""
Ascendra — Application Router.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.schemas import (
    ApplicationListResponse,
    ApplicationResponse,
    CreateApplicationRequest,
    TransitionApplicationRequest,
    UpdateApplicationRequest,
)
from app.core.schemas import MessageResponse
from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.applications.service import application_service

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_application(
    body: CreateApplicationRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new application (starts in DRAFT)."""
    app = await application_service.create(
        db=db, user_id=user.id, **body.model_dump()
    )
    return ApplicationResponse.model_validate(app)


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all applications with optional status filter."""
    items, total = await application_service.list_for_user(
        db=db, user_id=user.id, status=status, page=page, page_size=page_size
    )
    return ApplicationListResponse(
        items=[ApplicationResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats")
async def get_stats(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get application counts per status."""
    stats = await application_service.get_stats(db=db, user_id=user.id)
    return {"success": True, "data": stats}


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific application."""
    app = await application_service.get(db=db, app_id=app_id, user_id=user.id)
    return ApplicationResponse.model_validate(app)


@router.patch("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: str,
    body: UpdateApplicationRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update application fields."""
    app = await application_service.update(
        db=db, app_id=app_id, user_id=user.id,
        **body.model_dump(exclude_unset=True),
    )
    return ApplicationResponse.model_validate(app)


@router.post("/{app_id}/transition", response_model=ApplicationResponse)
async def transition_application(
    app_id: str,
    body: TransitionApplicationRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Transition application to a new status."""
    app = await application_service.transition(
        db=db, app_id=app_id, user_id=user.id, target_status=body.target_status
    )
    return ApplicationResponse.model_validate(app)


@router.delete("/{app_id}", response_model=MessageResponse)
async def archive_application(
    app_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive an application."""
    await application_service.archive(db=db, app_id=app_id, user_id=user.id)
    return MessageResponse(message="Application archived.")
