"""
Ascendra — Dashboard Schemas.
"""

from pydantic import BaseModel


class PipelineStats(BaseModel):
    draft: int = 0
    ready: int = 0
    sent: int = 0
    delivered: int = 0
    reply_received: int = 0
    interview: int = 0
    offer: int = 0
    rejected: int = 0
    total: int = 0


class CommunicationMetrics(BaseModel):
    """Email/outreach metrics for the dashboard."""
    emails_sent: int = 0
    emails_delivered: int = 0
    emails_failed: int = 0
    replies_received: int = 0
    reply_rate: float = 0.0  # percentage
    pending_followups: int = 0


class AIMetrics(BaseModel):
    """AI usage metrics for the dashboard."""
    total_generations: int = 0
    total_tokens_used: int = 0
    resume_generations: int = 0
    email_generations: int = 0


class DashboardOverview(BaseModel):
    pipeline: PipelineStats
    total_resumes: int = 0
    total_resume_versions: int = 0
    total_conversations: int = 0
    total_messages_sent: int = 0
    pending_approvals: int = 0
    communication: CommunicationMetrics | None = None
    ai_metrics: AIMetrics | None = None


class FunnelVelocityMetrics(BaseModel):
    # Average days an application spends in DRAFT before becoming READY/SENT
    avg_days_in_draft: float = 0.0
    # Average days from SENT to INTERVIEW
    avg_days_to_interview: float = 0.0
    # Average days from INTERVIEW to OFFER
    avg_days_to_offer: float = 0.0


class ActivityItem(BaseModel):
    type: str
    description: str
    timestamp: str
    entity_id: str | None = None
