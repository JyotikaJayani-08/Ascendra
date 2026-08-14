"""
Ascendra — Notification Schemas.
"""

from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    is_read: bool
    entity_type: str | None = None
    entity_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
