"""
Ascendra — Jobs Router.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.jobs.schemas import (
    CompanyResponse,
    CreateJobRequest,
    JobResponse,
    JobWithCompanyResponse,
    JobListResponse,
    SyncJobRequest,
    SyncJobResponse,
)
from app.jobs.service import job_service

router = APIRouter(tags=["Jobs"])


@router.get("/jobs", response_model=JobListResponse)
async def search_jobs(
    title: str | None = None,
    location: str | None = None,
    remote_status: str | None = None,
    employment_type: str | None = None,
    experience_level: str | None = None,
    company_name: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Search and filter jobs."""
    jobs, total = await job_service.search_jobs(
        db=db,
        user_id=user.id,
        title=title,
        location=location,
        remote_status=remote_status,
        employment_type=employment_type,
        experience_level=experience_level,
        company_name=company_name,
        page=page,
        page_size=page_size,
    )
    return JobListResponse(
        items=[JobWithCompanyResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/jobs/{job_id}", response_model=JobWithCompanyResponse)
async def get_job(
    job_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific job."""
    job = await job_service.get_job(db=db, job_id=job_id, user_id=user.id)
    return JobWithCompanyResponse.model_validate(job)


@router.post("/jobs", response_model=JobWithCompanyResponse, status_code=201)
async def create_job(
    body: CreateJobRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually create a job opportunity."""
    job = await job_service.create_manual_job(
        db=db, user_id=user.id, **body.model_dump()
    )
    return JobWithCompanyResponse.model_validate(job)


@router.post("/jobs/sync", response_model=SyncJobResponse)
async def sync_jobs(
    body: SyncJobRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin/Worker endpoint to synchronize jobs from an external provider."""
    result = await job_service.sync_provider_jobs(
        db=db,
        provider_name=body.provider_name,
        country_code=body.country_code,
        what=body.what,
        where=body.where,
        page=body.page,
        results_per_page=body.results_per_page,
        # SerpApi / Instahyre-grade filters
        query=body.query or body.what,
        location=body.location or body.where,
        is_remote=body.is_remote,
        company=body.company,
        experience_level=body.experience_level,
        employment_type=body.employment_type,
    )
    return SyncJobResponse(**result)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a job opportunity."""
    await job_service.delete_job(db=db, job_id=job_id, user_id=user.id)

