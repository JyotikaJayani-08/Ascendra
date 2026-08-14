"""
Ascendra — Dashboard Service.

Aggregation layer — never contains business logic, only reads and aggregates.
Provides real database metrics for the frontend dashboard per doc/10 §130-132.
"""

import logging
from collections import defaultdict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.models import Application, ApplicationStatus
from app.applications.service import application_service
from app.ai.models import AIGeneration
from app.core.models import AuditLog
from app.dashboard.schemas import (
    ActivityItem,
    AIMetrics,
    CommunicationMetrics,
    DashboardOverview,
    FunnelVelocityMetrics,
    PipelineStats,
)
from app.email.models import FollowUp, FollowUpStatus, Message, MessageStatus
from app.email.service import email_service
from app.resumes.service import resume_service

logger = logging.getLogger("ascendra.dashboard")


class DashboardService:
    """
    Read-only aggregation service for the dashboard.

    All methods perform SQL aggregations against real data.
    No mock data. No business logic mutations.
    """

    async def get_overview(
        self, db: AsyncSession, user_id: str
    ) -> DashboardOverview:
        """Build the main dashboard overview from real database aggregations."""

        # 1. Application pipeline stats — real counts per status
        status_counts = await application_service.get_stats(db, user_id)

        pipeline = PipelineStats(
            draft=status_counts.get(ApplicationStatus.DRAFT, 0),
            ready=status_counts.get(ApplicationStatus.READY, 0),
            sent=status_counts.get(ApplicationStatus.SENT, 0),
            delivered=status_counts.get(ApplicationStatus.DELIVERED, 0),
            reply_received=status_counts.get(ApplicationStatus.REPLY_RECEIVED, 0),
            interview=status_counts.get(ApplicationStatus.INTERVIEW, 0),
            offer=status_counts.get(ApplicationStatus.OFFER, 0),
            rejected=status_counts.get(ApplicationStatus.REJECTED, 0),
            total=sum(status_counts.values()),
        )

        # 2. Resume stats — real counts
        resume_stats = await resume_service.get_stats(db, user_id)

        # 3. Email stats — real counts
        email_stats = await email_service.get_stats(db, user_id)

        # 4. Pending approvals — messages in DRAFT or GENERATED status
        pending_result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.user_id == user_id,
                Message.status.in_([MessageStatus.DRAFT, MessageStatus.GENERATED]),
            )
        )
        pending_approvals = pending_result.scalar() or 0

        # 5. Communication metrics
        comm_metrics = await self._get_communication_metrics(db, user_id)

        # 6. AI metrics
        ai_metrics = await self._get_ai_metrics(db, user_id)

        return DashboardOverview(
            pipeline=pipeline,
            total_resumes=resume_stats.get("total_resumes", 0),
            total_resume_versions=resume_stats.get("total_resume_versions", 0),
            total_conversations=email_stats.get("total_conversations", 0),
            total_messages_sent=email_stats.get("total_messages_sent", 0),
            pending_approvals=pending_approvals,
            communication=comm_metrics,
            ai_metrics=ai_metrics,
        )

    async def _get_communication_metrics(
        self, db: AsyncSession, user_id: str
    ) -> CommunicationMetrics:
        """Aggregate email communication metrics."""
        # Emails sent
        sent_result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.user_id == user_id,
                Message.status.in_([MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.REPLIED]),
            )
        )
        emails_sent = sent_result.scalar() or 0

        # Emails delivered
        delivered_result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.user_id == user_id,
                Message.status == MessageStatus.DELIVERED,
            )
        )
        emails_delivered = delivered_result.scalar() or 0

        # Emails failed
        failed_result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.user_id == user_id,
                Message.status == MessageStatus.FAILED,
            )
        )
        emails_failed = failed_result.scalar() or 0

        # Replies received
        replied_result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.user_id == user_id,
                Message.status == MessageStatus.REPLIED,
            )
        )
        replies_received = replied_result.scalar() or 0

        # Reply rate
        reply_rate = round((replies_received / emails_sent * 100), 1) if emails_sent > 0 else 0.0

        # Pending follow-ups
        followup_result = await db.execute(
            select(func.count()).select_from(FollowUp).where(
                FollowUp.user_id == user_id,
                FollowUp.status == FollowUpStatus.SCHEDULED,
            )
        )
        pending_followups = followup_result.scalar() or 0

        return CommunicationMetrics(
            emails_sent=emails_sent,
            emails_delivered=emails_delivered,
            emails_failed=emails_failed,
            replies_received=replies_received,
            reply_rate=reply_rate,
            pending_followups=pending_followups,
        )

    async def _get_ai_metrics(
        self, db: AsyncSession, user_id: str
    ) -> AIMetrics:
        """Aggregate AI usage metrics."""
        # Total generations
        total_result = await db.execute(
            select(func.count()).select_from(AIGeneration).where(
                AIGeneration.user_id == user_id,
            )
        )
        total_generations = total_result.scalar() or 0

        # Total tokens
        tokens_result = await db.execute(
            select(func.coalesce(func.sum(AIGeneration.total_tokens), 0)).where(
                AIGeneration.user_id == user_id,
            )
        )
        total_tokens = tokens_result.scalar() or 0

        # Resume generations
        resume_result = await db.execute(
            select(func.count()).select_from(AIGeneration).where(
                AIGeneration.user_id == user_id,
                AIGeneration.generation_type == "resume",
            )
        )
        resume_generations = resume_result.scalar() or 0

        # Email generations
        email_result = await db.execute(
            select(func.count()).select_from(AIGeneration).where(
                AIGeneration.user_id == user_id,
                AIGeneration.generation_type == "email",
            )
        )
        email_generations = email_result.scalar() or 0

        return AIMetrics(
            total_generations=total_generations,
            total_tokens_used=total_tokens,
            resume_generations=resume_generations,
            email_generations=email_generations,
        )

    async def get_funnel_velocity(
        self, db: AsyncSession, user_id: str
    ) -> FunnelVelocityMetrics:
        """Calculate the average time spent in each funnel stage."""

        # Fetch all transition logs for the user
        result = await db.execute(
            select(AuditLog)
            .where(
                AuditLog.user_id == user_id,
                AuditLog.action == "APPLICATION_TRANSITIONED"
            )
            .order_by(AuditLog.resource_id, AuditLog.created_at)
        )
        logs = result.scalars().all()

        # Group by app_id
        app_timelines = defaultdict(list)
        for log in logs:
            if not log.details:
                continue
            new_status = log.details.get("new_status")
            if new_status:
                app_timelines[log.resource_id].append((new_status, log.created_at))

        # Also need the app creation times to calculate time in DRAFT.
        apps_result = await db.execute(
            select(Application.id, Application.created_at).where(Application.user_id == user_id)
        )
        app_creation_times = {row.id: row.created_at for row in apps_result}

        draft_durations = []
        interview_durations = []
        offer_durations = []

        for app_id, timeline in app_timelines.items():
            if not timeline:
                continue

            created_at = app_creation_times.get(app_id)
            if not created_at:
                continue

            # Find first time it left DRAFT (became READY or SENT)
            first_non_draft = next((t for s, t in timeline if s in ("READY", "SENT")), None)
            if first_non_draft:
                draft_durations.append((first_non_draft - created_at).total_seconds() / 86400)

            # Find time it became SENT
            sent_time = next((t for s, t in timeline if s == "SENT"), None)
            # Find time it became INTERVIEW
            interview_time = next((t for s, t in timeline if s == "INTERVIEW"), None)
            if sent_time and interview_time and interview_time > sent_time:
                interview_durations.append((interview_time - sent_time).total_seconds() / 86400)

            # Find time it became OFFER
            offer_time = next((t for s, t in timeline if s == "OFFER"), None)
            if interview_time and offer_time and offer_time > interview_time:
                offer_durations.append((offer_time - interview_time).total_seconds() / 86400)

        return FunnelVelocityMetrics(
            avg_days_in_draft=round(sum(draft_durations)/len(draft_durations), 1) if draft_durations else 0.0,
            avg_days_to_interview=round(sum(interview_durations)/len(interview_durations), 1) if interview_durations else 0.0,
            avg_days_to_offer=round(sum(offer_durations)/len(offer_durations), 1) if offer_durations else 0.0,
        )

    async def get_recent_activity(
        self, db: AsyncSession, user_id: str, limit: int = 15
    ) -> list[ActivityItem]:
        """
        Retrieve the user's recent activity timeline (doc/10 §133).

        Returns the most recent audit log entries formatted as
        human-readable activity items.
        """
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        logs = result.scalars().all()

        items = []
        for log in logs:
            description = self._format_activity_description(log)
            items.append(ActivityItem(
                type=log.action,
                description=description,
                timestamp=log.created_at.isoformat() if log.created_at else "",
                entity_id=log.resource_id,
            ))
        return items

    # ── Private Helpers ───────────────────────────────────────

    @staticmethod
    def _format_activity_description(log: AuditLog) -> str:
        """Convert an audit log entry into a human-readable description."""
        action = log.action
        details = log.details or {}

        description_map = {
            "APPLICATION_CREATED": "Created a new application",
            "APPLICATION_TRANSITIONED": f"Application moved to {details.get('new_status', 'unknown')}",
            "RESUME_UPLOADED": "Uploaded a new resume",
            "RESUME_PARSED": "Resume parsing completed",
            "EMAIL_SENT": f"Email sent to {details.get('recipient', 'recipient')}",
            "EMAIL_FAILED": f"Email delivery failed: {details.get('error', 'unknown error')}",
            "JOB_CREATED": f"Added job: {details.get('title', 'untitled')}",
            "CONTACT_DISCOVERED": f"Discovered {details.get('count', 0)} contacts",
        }

        return description_map.get(action, action.replace("_", " ").title())


dashboard_service = DashboardService()
