"""
Ascendra — Audit Service.

Helper module for recording immutable audit logs for security and compliance.
"""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import AuditLog

logger = logging.getLogger("ascendra.audit")


async def log_audit_event(
    db: AsyncSession,
    user_id: Optional[str],
    event_type: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Asynchronously record an immutable audit log entry.
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=event_type,
            resource_type=entity_type,
            resource_id=entity_id,
            details=metadata_json or {},
        )
        db.add(audit_entry)
        await db.commit()
        logger.info(f"Audit log recorded: [{event_type}] {entity_type} {entity_id or ''} by user {user_id or 'system'}")
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
        # Audit failures shouldn't break the main transaction if committed separately, but raise or log safely
        return None
