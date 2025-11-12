from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field


class NotificationEvent(BaseModel):
        """Schema for the message consumed from the push.queue.

        Notes:
        - `template_id` and `payload` are made optional to preserve backwards
            compatibility with messages that contain an inline `payload` but no
            `template_id`. The worker will resolve a payload using either the
            provided `template_id` (and variables) or the inline `payload`.
        """
        event_id: UUID = Field(description="Unique ID for tracking the notification.")
        user_id: int
        template_id: Optional[str] = None
        payload: Optional[dict] = None
        created_at: datetime
    
class TokenValidation(BaseModel):
    token: str = Field(description="Device push token (FCM/APNs).")
    is_valid: bool
    last_validated: datetime

class HealthStatus(BaseModel):
    service: str = "Push Service"
    status: str
    rabbit_connected: bool
    redis_connected: bool
    timestamp: datetime