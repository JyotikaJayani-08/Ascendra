"""
Ascendra — Resume Router.
"""

from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.limiter import limiter

from app.core.schemas import MessageResponse
from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.resumes.schemas import (
    ResumeResponse,
    ResumeVersionResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    ResumeCompareResponse,
)
from app.resumes.service import resume_service
from app.resumes.models import ResumeStatus

router = APIRouter(tags=["Resumes"])


# ── Resumes ───────────────────────────────────────────────────

@router.post("/resumes", response_model=ResumeResponse, status_code=201)
@limiter.limit("10/minute")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new resume (PDF only, max 5 MB)."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the 5MB limit.")
        
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the 5MB limit.")
        
    # Verify PDF magic bytes header
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file format. PDF header signature (%PDF) not found.")

    resume = await resume_service.upload_resume(
        db=db,
        user_id=user.id,
        filename=file.filename or "resume.pdf",
        file_content=content,
        mime_type="application/pdf",
    )

    # Dispatch parsing background task immediately (non-blocking asyncio event loop)
    import asyncio
    from app.workers.resume_tasks import _process_uploaded_resume_async
    asyncio.create_task(_process_uploaded_resume_async(resume.id))

    return ResumeResponse.model_validate(resume)


@router.get("/resumes", response_model=list[ResumeResponse])
async def list_resumes(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all resumes for the current user."""
    resumes = await resume_service.get_user_resumes(db=db, user_id=user.id)
    return [ResumeResponse.model_validate(r) for r in resumes]


@router.get("/resumes/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific resume."""
    resume = await resume_service.get_resume(db=db, resume_id=resume_id, user_id=user.id)
    return ResumeResponse.model_validate(resume)


@router.delete("/resumes/delete-all", response_model=MessageResponse)
async def delete_all_resumes(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all uploaded resumes for the current user."""
    count = await resume_service.delete_all_resumes(db=db, user_id=user.id)
    return MessageResponse(message=f"Deleted {count} resumes.")


@router.post("/resumes/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_resumes(
    body: BulkDeleteRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk delete specific uploaded resumes."""
    count = await resume_service.bulk_delete_resumes(
        db=db, resume_ids=body.ids, user_id=user.id
    )
    return BulkDeleteResponse(
        deleted_count=count, message=f"Bulk deleted {count} resumes."
    )


@router.delete("/resumes/{resume_id}", response_model=MessageResponse)
async def delete_resume(
    resume_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a resume."""
    await resume_service.delete_resume(db=db, resume_id=resume_id, user_id=user.id)
    return MessageResponse(message="Resume deleted.")


@router.post("/resumes/{resume_id}/reparse", response_model=ResumeResponse)
async def reparse_resume(
    resume_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-trigger background parsing for an uploaded resume."""
    resume = await resume_service.get_resume(db=db, resume_id=resume_id, user_id=user.id)
    if resume.status != ResumeStatus.PARSED:
        resume.status = ResumeStatus.UPLOADED
        await db.commit()
    import asyncio
    from app.workers.resume_tasks import _process_uploaded_resume_async
    asyncio.create_task(_process_uploaded_resume_async(resume.id))
    return ResumeResponse.model_validate(resume)


# ── Resume Versions ───────────────────────────────────────────

@router.get("/resume-versions", response_model=list[ResumeVersionResponse])
async def list_all_user_versions(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all AI tailored versions for the current user."""
    versions = await resume_service.get_all_user_versions(
        db=db, user_id=user.id
    )
    return [ResumeVersionResponse.model_validate(v) for v in versions]


@router.get("/resumes/{resume_id}/versions", response_model=list[ResumeVersionResponse])
async def list_versions(
    resume_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all versions of a resume."""
    versions = await resume_service.get_resume_versions(
        db=db, resume_id=resume_id, user_id=user.id
    )
    return [ResumeVersionResponse.model_validate(v) for v in versions]


@router.post("/resume-versions/{version_id}/approve", response_model=ResumeVersionResponse)
async def approve_version(
    version_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a generated resume version."""
    version = await resume_service.approve_version(
        db=db, version_id=version_id, user_id=user.id
    )
    return ResumeVersionResponse.model_validate(version)


@router.delete("/resume-versions/delete-all", response_model=MessageResponse)
async def delete_all_versions(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all tailored resume versions for the current user."""
    count = await resume_service.delete_all_versions(db=db, user_id=user.id)
    return MessageResponse(message=f"Deleted {count} resume versions.")


@router.post("/resume-versions/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_versions(
    body: BulkDeleteRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk delete specific tailored resume versions."""
    count = await resume_service.bulk_delete_versions(
        db=db, version_ids=body.ids, user_id=user.id
    )
    return BulkDeleteResponse(
        deleted_count=count, message=f"Bulk deleted {count} resume versions."
    )


@router.delete("/resume-versions/{version_id}", response_model=MessageResponse)
async def delete_version(
    version_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an AI-generated resume version."""
    await resume_service.delete_version(db=db, version_id=version_id, user_id=user.id)
    return MessageResponse(message="Resume version deleted.")


@router.get("/resume-versions/{version_id}/compare", response_model=ResumeCompareResponse)
async def compare_version(
    version_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get backend structural comparison diff between a tailored resume version and its original base resume."""
    result = await resume_service.compare_version_with_original(
        db=db, version_id=version_id, user_id=user.id
    )
    return ResumeCompareResponse.model_validate(result)


