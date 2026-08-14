"""
Ascendra — AI Router.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.limiter import limiter

from app.ai.schemas import GenerateEmailRequest, GenerateFollowUpRequest, GenerateResumeRequest
from app.ai.service import ai_service
from app.core.dependencies import get_current_active_user
from app.database import get_db

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/resume/generate")
@limiter.limit("5/minute")
async def generate_resume(
    request: Request,
    body: GenerateResumeRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI-optimized resume version."""
    result = await ai_service.generate_resume_flow(
        db=db,
        user_id=user.id,
        resume_id=body.resume_id,
        job_id=body.job_id,
        label=body.label,
        tailoring_style=body.tailoring_style,
        focus_keywords=body.focus_keywords,
        custom_instructions=body.custom_instructions,
    )
    await db.commit()
    return {
        "success": True,
        "data": result,
    }


@router.post("/email/generate")
@limiter.limit("10/minute")
async def generate_email(
    request: Request,
    body: GenerateEmailRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a personalized outreach email for an application."""
    result = await ai_service.generate_email_flow(
        db=db,
        user_id=user.id,
        application_id=body.application_id,
        tone=body.tone,
    )
    await db.commit()
    return {
        "success": True,
        "data": result,
    }


@router.post("/email/followup")
@limiter.limit("10/minute")
async def generate_followup_email(
    request: Request,
    body: GenerateFollowUpRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a follow-up email for an existing conversation."""
    result = await ai_service.generate_followup_flow(
        db=db,
        user_id=user.id,
        conversation_id=body.conversation_id,
        follow_up_number=body.follow_up_number,
        tone=body.tone,
    )
    await db.commit()
    return {
        "success": True,
        "data": result,
    }

