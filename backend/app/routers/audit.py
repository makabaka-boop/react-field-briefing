from fastapi import APIRouter, Query
from typing import List, Optional
import json
from ..database import get_db
from ..schemas import AuditEvent

router = APIRouter()


@router.get("/audit-events", response_model=List[AuditEvent])
def list_audit_events(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    with get_db() as db:
        sql = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type)
        if entity_id is not None:
            sql += " AND entity_id = ?"
            params.append(entity_id)
        if action:
            sql += " AND action = ?"
            params.append(action)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = db.execute(sql, params).fetchall()
    return [
        {
            "id": r["id"],
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "action": r["action"],
            "actor": r["actor"],
            "details": json.loads(r["details"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]
