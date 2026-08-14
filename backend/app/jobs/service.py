"""
Ascendra — Jobs Service.
"""

import logging

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFound
from app.jobs.models import Company, Job, JobStatus, RemoteStatus, EmploymentType, ExperienceLevel

logger = logging.getLogger("ascendra.jobs")


def _normalize_remote_status(val: str | None) -> RemoteStatus:
    if isinstance(val, RemoteStatus):
        return val
    if not val:
        return RemoteStatus.UNKNOWN
    s = str(val).strip().upper().replace("-", "_").replace(" ", "_")
    if "REMOTE" in s or "WFH" in s or "TELECOMMUTE" in s:
        return RemoteStatus.REMOTE
    if "HYBRID" in s:
        return RemoteStatus.HYBRID
    if "ONSITE" in s or "ON_SITE" in s or "OFFICE" in s:
        return RemoteStatus.ONSITE
    try:
        return RemoteStatus[s]
    except KeyError:
        return RemoteStatus.UNKNOWN


def _normalize_employment_type(val: str | None) -> EmploymentType:
    if isinstance(val, EmploymentType):
        return val
    if not val:
        return EmploymentType.UNKNOWN
    s = str(val).strip().upper().replace("-", "_").replace(" ", "_")
    if "FULL" in s:
        return EmploymentType.FULL_TIME
    if "PART" in s:
        return EmploymentType.PART_TIME
    if "CONTRACT" in s or "TEMP" in s:
        return EmploymentType.CONTRACT
    if "INTERN" in s:
        return EmploymentType.INTERNSHIP
    if "FREELANCE" in s:
        return EmploymentType.FREELANCE
    try:
        return EmploymentType[s]
    except KeyError:
        return EmploymentType.UNKNOWN


def _normalize_experience_level(val: str | None) -> ExperienceLevel:
    if isinstance(val, ExperienceLevel):
        return val
    if not val:
        return ExperienceLevel.UNKNOWN
    s = str(val).strip().upper().replace("-", "_").replace(" ", "_")
    if "ENTRY" in s or "JUNIOR" in s or "JR" in s:
        return ExperienceLevel.ENTRY
    if "MID" in s:
        return ExperienceLevel.MID
    if "SENIOR" in s or "SR" in s:
        return ExperienceLevel.SENIOR
    if "LEAD" in s or "PRINCIPAL" in s:
        return ExperienceLevel.LEAD
    if "EXEC" in s or "DIRECTOR" in s:
        return ExperienceLevel.EXECUTIVE
    try:
        return ExperienceLevel[s]
    except KeyError:
        return ExperienceLevel.UNKNOWN


def _clean_salary_currency(val: str | None) -> str | None:
    if not val:
        return None
    s = str(val).strip().upper()
    if len(s) <= 3 and s.isalpha():
        return s
    if "$" in s or "USD" in s:
        return "USD"
    if "₹" in s or "INR" in s or "RS" in s:
        return "INR"
    if "€" in s or "EUR" in s:
        return "EUR"
    if "£" in s or "GBP" in s:
        return "GBP"
    return None


class JobService:

    async def search_jobs(
        self,
        db: AsyncSession,
        user_id: str,
        title: str | None = None,
        location: str | None = None,
        remote_status: str | None = None,
        employment_type: str | None = None,
        experience_level: str | None = None,
        company_name: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Job], int]:
        """Search/filter jobs with pagination."""
        query = (
            select(Job)
            .options(joinedload(Job.company))
            .where(
                Job.status == JobStatus.ACTIVE,
                or_(Job.user_id == user_id, Job.user_id == None)
            )
        )

        if title:
            pattern = f"%{title}%"
            query = query.outerjoin(Company).where(
                or_(
                    Job.title.ilike(pattern),
                    Job.description.ilike(pattern),
                    Company.name.ilike(pattern)
                )
            )
        if location:
            loc_pattern = f"%{location}%"
            query = query.where(
                or_(
                    Job.location.ilike(loc_pattern),
                    Job.remote_status == "REMOTE",
                    Job.location.ilike("%Remote%")
                )
            )
        if remote_status:
            query = query.where(Job.remote_status == remote_status)
        if employment_type:
            query = query.where(Job.employment_type == employment_type)
        if experience_level:
            query = query.where(Job.experience_level == experience_level)
        if company_name:
            query = query.outerjoin(Company).where(Company.name.ilike(f"%{company_name}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        query = query.order_by(Job.updated_at.desc(), Job.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        return list(result.unique().scalars().all()), total

    async def get_job(self, db: AsyncSession, job_id: str, user_id: str) -> Job:
        """Get a single job with company info."""
        result = await db.execute(
            select(Job)
            .options(joinedload(Job.company))
            .where(
                Job.id == job_id,
                or_(Job.user_id == user_id, Job.user_id == None)
            )
        )
        job = result.unique().scalar_one_or_none()
        if not job:
            raise NotFound("Job")
        return job

    async def create_manual_job(
        self,
        db: AsyncSession,
        title: str,
        company_name: str,
        user_id: str | None = None,
        description: str | None = None,
        requirements: str | None = None,
        location: str | None = None,
        remote_status: str = "UNKNOWN",
        employment_type: str = "UNKNOWN",
        experience_level: str = "UNKNOWN",
        source_url: str | None = None,
        salary_min: int | None = None,
        salary_max: int | None = None,
        salary_currency: str | None = None,
    ) -> Job:
        """Manually create a job + company if needed."""
        # Find or create company
        result = await db.execute(
            select(Company).where(Company.name.ilike(company_name))
        )
        company = result.scalar_one_or_none()
        if not company:
            company = Company(name=company_name)
            db.add(company)
            await db.flush()

        job = Job(
            user_id=user_id,
            company_id=company.id,
            title=title,
            description=description,
            requirements=requirements,
            location=location,
            remote_status=_normalize_remote_status(remote_status),
            employment_type=_normalize_employment_type(employment_type),
            experience_level=_normalize_experience_level(experience_level),
            source_url=source_url,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            provider_name="MANUAL",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job.company = company

        logger.info(f"Manual job created: {title} @ {company_name}")
        return job

    async def get_company_jobs(
        self, db: AsyncSession, company_id: str, user_id: str
    ) -> list[Job]:
        """List all active jobs for a company."""
        result = await db.execute(
            select(Job)
            .where(Job.company_id == company_id, Job.status == JobStatus.ACTIVE, or_(Job.user_id == user_id, Job.user_id == None))
            .order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())

    async def sync_provider_jobs(
        self,
        db: AsyncSession,
        provider_name: str,
        **kwargs
    ) -> dict:
        """Fetch jobs from external provider and ingest into database with deduplication."""
        provider = None
        p_name = provider_name.lower().strip()
        if p_name in ["serpapi", "google_jobs", "serpapi_google_jobs"]:
            from app.providers.jobs.serpapi_google_jobs import serpapi_job_provider
            provider = serpapi_job_provider
        elif p_name == "remotive":
            from app.providers.jobs.remotive_jobicy import remotive_provider
            provider = remotive_provider
        elif p_name == "jobicy":
            from app.providers.jobs.remotive_jobicy import jobicy_provider
            provider = jobicy_provider
        elif p_name == "remoteok":
            from app.providers.jobs.remoteok import remoteok_provider
            provider = remoteok_provider
        elif p_name in ["weworkremotely", "wwr"]:
            from app.providers.jobs.weworkremotely import weworkremotely_provider
            provider = weworkremotely_provider
        else:
            raise ValueError(f"Unknown job provider: {provider_name}")
            
        normalized_jobs = await provider.fetch_jobs(**kwargs)
        if not normalized_jobs:
            return {"synced": 0, "skipped_or_updated": 0, "provider": provider_name}
            
        synced_count = 0
        skipped_count = 0
        
        for nj in normalized_jobs:
            # 1. Find or create company
            company_name = nj.company_name or "Unknown Company"
            comp_result = await db.execute(select(Company).where(Company.name.ilike(company_name)))
            company = comp_result.scalar_one_or_none()
            if not company:
                company = Company(name=company_name)
                db.add(company)
                await db.flush()
                
            # 2. Deduplicate Job
            conditions = []
            if nj.external_id:
                conditions.append((Job.external_id == nj.external_id) & (Job.provider_name == provider.provider_name))
            if nj.source_url:
                conditions.append(Job.source_url == nj.source_url)
                
            if not conditions:
                continue
                
            job_result = await db.execute(select(Job).where(or_(*conditions)))
            existing_job = job_result.scalar_one_or_none()
            
            if existing_job:
                from datetime import datetime, timezone
                existing_job.title = (nj.title or "Untitled Role")[:500]
                existing_job.description = nj.description
                existing_job.remote_status = _normalize_remote_status(nj.remote_status)
                existing_job.updated_at = datetime.now(timezone.utc)
                skipped_count += 1
            else:
                curr = _clean_salary_currency(nj.salary_currency)
                ext_id = nj.external_id[:255] if nj.external_id else None
                src_url = nj.source_url[:1000] if nj.source_url else None
                job_title = (nj.title or "Untitled Role")[:500]
                loc = nj.location[:255] if nj.location else None

                new_job = Job(
                    company_id=company.id,
                    title=job_title,
                    description=nj.description,
                    location=loc,
                    remote_status=_normalize_remote_status(nj.remote_status),
                    employment_type=_normalize_employment_type(nj.employment_type),
                    experience_level=_normalize_experience_level(getattr(nj, "experience_level", None)),
                    salary_min=nj.salary_min,
                    salary_max=nj.salary_max,
                    salary_currency=curr,
                    source_url=src_url,
                    provider_name=provider.provider_name,
                    external_id=ext_id,
                    provider_metadata=nj.provider_metadata,
                )
                db.add(new_job)
                synced_count += 1
                
        await db.commit()
        logger.info(f"Sync complete for {provider_name}. Synced: {synced_count}, Skipped/Updated: {skipped_count}")
        return {"synced": synced_count, "skipped_or_updated": skipped_count, "provider": provider_name}

    async def delete_job(self, db: AsyncSession, job_id: str, user_id: str) -> None:
        """Delete a job created by the user."""
        job = await self.get_job(db=db, job_id=job_id, user_id=user_id)
        await db.delete(job)
        await db.commit()
        logger.info(f"Job deleted: {job_id}")


job_service = JobService()
