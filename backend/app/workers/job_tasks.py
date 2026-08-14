"""
Ascendra — Job Celery Tasks.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.jobs.service import job_service
from app.providers.jobs.remoteok import remoteok_provider
from app.workers.celery_app import celery_app

logger = logging.getLogger("ascendra.workers.jobs")


async def _sync_provider_jobs_async():
    """Async implementation to fetch jobs and store them."""
    async with async_session_factory() as db:
        try:
            jobs = await remoteok_provider.fetch_jobs()
            count = 0
            for job in jobs:
                try:
                    await job_service.create_manual_job(
                        db=db,
                        title=job.title,
                        company_name=job.company_name,
                        description=job.description,
                        location=job.location,
                        remote_status=job.remote_status,
                        employment_type=job.employment_type,
                        source_url=job.source_url,
                        # Pass any other available metadata
                    )
                    count += 1
                except Exception as inner_e:
                    logger.warning(f"Failed to insert job {job.title}: {inner_e}")
                    
            logger.info(f"Successfully synced {count} jobs from RemoteOK.")
        except Exception as e:
            logger.error(f"Job sync failed: {e}")


@celery_app.task
def sync_provider_jobs_task():
    """
    Background task to run periodically and fetch jobs from RemoteOK.
    """
    from asgiref.sync import async_to_sync
    async_to_sync(_sync_provider_jobs_async)()
