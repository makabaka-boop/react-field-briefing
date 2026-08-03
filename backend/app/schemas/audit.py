from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    action: str
    actor: str
    from_status: str
    to_status: str
    event_metadata: dict[str, Any]
    created_at: datetime
