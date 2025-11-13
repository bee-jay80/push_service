from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional
from pydantic import BaseModel, Field


class NotificationEvent(BaseModel):
    """Schema for the message consumed from the push.queue.

    Notes:
    - `template_id` and `payload` are made optional to preserve backwards
        compatibility with messages that contain an inline `payload` but no
        `template_id`. The worker will resolve a payload using either the
        provided `template_id` (and variables) or the inline `payload`.
    - `event_id` and `created_at` are optional and will use sensible defaults
        if not provided by the publisher.
    - `user_id` is coerced to int if possible (e.g., from string or int input).
    """
    event_id: Optional[UUID] = Field(default_factory=uuid4, description="Unique ID for tracking the notification.")
    user_id: int | str = Field(description="User identifier; coerced to int if possible.")
    template_id: Optional[str] = None
    payload: Optional[dict] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Event creation timestamp; defaults to now.")

    def model_post_init(self, __context):
        """Post-validation hook to coerce user_id to int and log defaults used."""
        # Coerce user_id to int if it's a string
        if isinstance(self.user_id, str):
            try:
                self.user_id = int(self.user_id)
            except (ValueError, TypeError):
                # If it can't be converted, leave as string and log a warning
                print(f"⚠️ user_id '{self.user_id}' could not be converted to int; keeping as string")
    
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