"""
Ascendra — Application Service.

The heart of the system. All application lifecycle management.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.models import Application, ApplicationStatus
from app.core.exceptions import InvalidStateTransition, NotFound, PermissionDenied
from app.core.state_machine import ApplicationStateMachine
from app.core.audit import log_audit_event
from app.jobs.models import Job
from app.jobs.service import job_service

logger = logging.getLogger("ascendra.applications")


class ApplicationService:

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        job_id: str,
        resume_version_id: str | None = None,
        contact_id: str | None = None,
        notes: str | None = None,
    ) -> Application:
        """Create a new application in DRAFT state."""
        # Verify job exists and capture snapshot
        job = await job_service.get_job(db=db, job_id=job_id, user_id=user_id)
        company_name = job.company.name if job.company else None

        app = Application(
            user_id=user_id,
            job_id=job_id,
            resume_version_id=resume_version_id,
            contact_id=contact_id,
            notes=notes,
            status=ApplicationStatus.DRAFT,
            company_name_snapshot=company_name,
            job_title_snapshot=job.title,
        )
        db.add(app)
        await db.commit()
        await db.refresh(app)

        await log_audit_event(
            db=db,
            user_id=user_id,
            event_type="APPLICATION_CREATED",
            entity_type="APPLICATION",
            entity_id=app.id,
            metadata_json={"job_id": job_id, "job_title": job.title, "company": company_name},
        )

        logger.info(f"Application created: {app.id[:8]} for job {job.title}")
        return app

    async def get(
        self, db: AsyncSession, app_id: str, user_id: str
    ) -> Application:
        """Get a single application, verifying ownership."""
        result = await db.execute(
            select(Application).where(Application.id == app_id)
        )
        app = result.scalar_one_or_none()
        if not app:
            raise NotFound("Application")
        if app.user_id != user_id:
            raise PermissionDenied()
        return app

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Application], int]:
        """List applications with optional status filter and pagination."""
        query = select(Application).where(
            Application.user_id == user_id,
            Application.status != ApplicationStatus.ARCHIVED,
        )
        count_query = select(func.count()).select_from(Application).where(
            Application.user_id == user_id,
            Application.status != ApplicationStatus.ARCHIVED,
        )

        if status:
            query = query.where(Application.status == status)
            count_query = count_query.where(Application.status == status)

        # Total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginated results
        query = query.order_by(Application.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)

        return list(result.scalars().all()), total

    async def update(
        self,
        db: AsyncSession,
        app_id: str,
        user_id: str,
        resume_version_id: str | None = None,
        contact_id: str | None = None,
        notes: str | None = None,
    ) -> Application:
        """Update mutable fields of an application."""
        app = await self.get(db, app_id, user_id)

        if resume_version_id is not None:
            app.resume_version_id = resume_version_id
        if contact_id is not None:
            app.contact_id = contact_id
        if notes is not None:
            app.notes = notes

        await db.commit()
        await db.refresh(app)
        return app

    async def transition(
        self,
        db: AsyncSession,
        app_id: str,
        user_id: str,
        target_status: str,
    ) -> Application:
        """Transition application to a new state. Validates the transition."""
        app = await self.get(db, app_id, user_id)

        # Validate state machine guard rules
        ApplicationStateMachine.validate_transition(app.status, target_status)

        old_status = app.status
        app.status = target_status
        await db.commit()
        await db.refresh(app)

        await log_audit_event(
            db=db,
            user_id=user_id,
            event_type="APPLICATION_TRANSITIONED",
            entity_type="APPLICATION",
            entity_id=app.id,
            metadata_json={"old_status": old_status, "new_status": target_status},
        )

        logger.info(f"Application {app_id[:8]} → {target_status}")
        return app

    async def archive(
        self, db: AsyncSession, app_id: str, user_id: str
    ) -> Application:
        """Archive an application."""
        return await self.transition(db, app_id, user_id, ApplicationStatus.ARCHIVED)

    async def get_stats(
        self, db: AsyncSession, user_id: str
    ) -> dict[str, int]:
        """Get application count per status for a user."""
        result = await db.execute(
            select(Application.status, func.count())
            .where(Application.user_id == user_id)
            .group_by(Application.status)
        )
        return {row[0]: row[1] for row in result.all()}


application_service = ApplicationService()
