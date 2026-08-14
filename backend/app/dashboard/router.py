"""
Ascendra — Dashboard Router.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.dashboard.schemas import ActivityItem, DashboardOverview, FunnelVelocityMetrics
from app.dashboard.service import dashboard_service
from app.database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardOverview)
async def get_dashboard(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the main dashboard overview."""
    return await dashboard_service.get_overview(db=db, user_id=user.id)


@router.get("/funnel-velocity", response_model=FunnelVelocityMetrics)
async def get_funnel_velocity(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the funnel velocity metrics."""
    return await dashboard_service.get_funnel_velocity(db=db, user_id=user.id)


@router.get("/recent-activity", response_model=list[ActivityItem])
async def get_recent_activity(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's recent activity timeline (doc/10 §133)."""
    return await dashboard_service.get_recent_activity(db=db, user_id=user.id)
