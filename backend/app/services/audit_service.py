from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.all_models import AuditEvent


def record(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: str = "system",
    from_status: str = "",
    to_status: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    event = AuditEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        from_status=from_status,
        to_status=to_status,
        event_metadata=metadata or {},
    )
    db.add(event)
    db.flush()
    return event
