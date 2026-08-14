"""
Ascendra — Celery Application.

Celery worker configuration with SSL support for Upstash Redis
and full SQLAlchemy model registry initialization.
"""

import ssl

from celery import Celery

from app.config import settings

# Import all models so SQLAlchemy metadata registry is fully initialized in Celery worker.
# This prevents NoReferencedTableError when workers process tasks.
import app.auth.models  # noqa: F401 — User, UserEmailConfig
import app.workspaces.models  # noqa: F401 — Workspace, WorkspaceMember
import app.jobs.models  # noqa: F401 — Job, Company
import app.applications.models  # noqa: F401 — Application
import app.resumes.models  # noqa: F401 — Resume, ResumeVersion
import app.email.models  # noqa: F401 — Conversation, Message, FollowUp
import app.notifications.models  # noqa: F401 — Notification
import app.core.models  # noqa: F401 — AuditLog
import app.notes.models  # noqa: F401 — Note

# Build SSL config for Upstash Redis (rediss:// scheme)
_broker_use_ssl = None
_backend_use_ssl = None
if settings.REDIS_URL.startswith("rediss://"):
    _broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}
    _backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

celery_app = Celery(
    "ascendra_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.email_tasks",
        "app.workers.resume_tasks",
        "app.workers.job_tasks",
        "app.workers.contact_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    # SSL configuration for Upstash Redis broker
    broker_use_ssl=_broker_use_ssl,
    redis_backend_use_ssl=_backend_use_ssl,
    # Improve Upstash Redis resilience (serverless Redis closes idle connections)
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "socket_keepalive": True,
        "socket_keepalive_options": {},
        "retry_on_timeout": True,
    },
)

from celery.signals import after_setup_logger
from app.core.logging import setup_logging


@after_setup_logger.connect
def setup_celery_logging(logger, **kwargs):
    setup_logging(log_filename="celery.log")
