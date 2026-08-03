from fastapi import APIRouter, Query
from typing import List, Optional
import json
from ..database import get_db
from ..schemas import FindingCreate, FindingUpdate, Finding
from ..errors import NotFoundError, ValidationError
from ..state_machine import transition_finding
from ..audit import record_audit

router = APIRouter()

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
REQUIRED_FIELDS = ["category", "description", "risk_level", "reported_by"]


def validate_finding_fields(category=None, description=None, risk_level=None, reported_by=None, partial=False):
    errors = {}
    if not partial or category is not None:
        if not category or not str(category).strip():
            errors["category"] = "category cannot be empty"
    if not partial or description is not None:
        if not description or not str(description).strip():
            errors["description"] = "description cannot be empty"
    if not partial or risk_level is not None:
        if not risk_level or not str(risk_level).strip():
            errors["risk_level"] = "risk_level cannot be empty"
        elif risk_level not in VALID_RISK_LEVELS:
            errors["risk_level"] = f"risk_level must be one of {sorted(VALID_RISK_LEVELS)}"
    if not partial or reported_by is not None:
        if not reported_by or not str(reported_by).strip():
            errors["reported_by"] = "reported_by cannot be empty"
    if errors:
        raise ValidationError("Finding validation failed", errors)


def row_to_finding(row):
    return {
        "id": row["id"],
        "site_id": row["site_id"],
        "category": row["category"],
        "description": row["description"],
        "risk_level": row["risk_level"],
        "finding_status": row["finding_status"],
        "reported_by": row["reported_by"],
        "reported_at": row["reported_at"],
    }


@router.post("/findings", response_model=Finding)
def create_finding(payload: FindingCreate):
    validate_finding_fields(
        category=payload.category,
        description=payload.description,
        risk_level=payload.risk_level,
        reported_by=payload.reported_by,
    )
    with get_db() as db:
        site = db.execute("SELECT id FROM sites WHERE id = ?", (payload.site_id,)).fetchone()
        if not site:
            raise NotFoundError("site", payload.site_id)
        cur = db.execute(
            "INSERT INTO findings (site_id, category, description, risk_level, finding_status, reported_by) VALUES (?, ?, ?, ?, 'draft', ?)",
            (payload.site_id, payload.category.strip(), payload.description.strip(), payload.risk_level, payload.reported_by.strip()),
        )
        fid = cur.lastrowid
        record_audit(db, "finding", fid, "create_draft", payload.reported_by, {
            "site_id": payload.site_id,
            "category": payload.category,
            "risk_level": payload.risk_level,
            "note": "创建观察项草稿",
        })
        row = db.execute("SELECT * FROM findings WHERE id = ?", (fid,)).fetchone()
    return row_to_finding(row)


@router.get("/findings", response_model=List[Finding])
def list_findings(
    site_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    finding_status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
):
    with get_db() as db:
        sql = "SELECT f.* FROM findings f JOIN sites s ON f.site_id = s.id WHERE 1=1"
        params = []
        if site_id is not None:
            sql += " AND f.site_id = ?"
            params.append(site_id)
        if project_id is not None:
            sql += " AND s.project_id = ?"
            params.append(project_id)
        if finding_status:
            sql += " AND f.finding_status = ?"
            params.append(finding_status)
        if risk_level:
            sql += " AND f.risk_level = ?"
            params.append(risk_level)
        sql += " ORDER BY f.reported_at DESC"
        rows = db.execute(sql, params).fetchall()
    return [row_to_finding(r) for r in rows]


@router.get("/findings/{finding_id}", response_model=Finding)
def get_finding(finding_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    if not row:
        raise NotFoundError("finding", finding_id)
    return row_to_finding(row)


@router.patch("/findings/{finding_id}", response_model=Finding)
def update_finding(finding_id: int, payload: FindingUpdate):
    with get_db() as db:
        row = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
        if not row:
            raise NotFoundError("finding", finding_id)

        merged = {
            "category": payload.category if payload.category is not None else row["category"],
            "description": payload.description if payload.description is not None else row["description"],
            "risk_level": payload.risk_level if payload.risk_level is not None else row["risk_level"],
            "reported_by": payload.reported_by if payload.reported_by is not None else row["reported_by"],
        }
        validate_finding_fields(
            category=merged["category"],
            description=merged["description"],
            risk_level=merged["risk_level"],
            reported_by=merged["reported_by"],
        )

        updates = []
        params = []
        changed_fields = []
        if payload.category is not None and payload.category != row["category"]:
            updates.append("category = ?")
            params.append(payload.category.strip())
            changed_fields.append("category")
        if payload.description is not None and payload.description != row["description"]:
            updates.append("description = ?")
            params.append(payload.description.strip())
            changed_fields.append("description")
        if payload.risk_level is not None and payload.risk_level != row["risk_level"]:
            updates.append("risk_level = ?")
            params.append(payload.risk_level)
            changed_fields.append("risk_level")
        if payload.reported_by is not None and payload.reported_by != row["reported_by"]:
            updates.append("reported_by = ?")
            params.append(payload.reported_by.strip())
            changed_fields.append("reported_by")
        if updates:
            params.append(finding_id)
            db.execute(f"UPDATE findings SET {', '.join(updates)} WHERE id = ?", params)
            record_audit(db, "finding", finding_id, "update", "", {
                "changed_fields": changed_fields,
                "note": "更新观察项字段",
            })
        row = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    return row_to_finding(row)


@router.post("/findings/{finding_id}/save-draft", response_model=Finding)
def save_draft(finding_id: int, payload: FindingUpdate):
    return update_finding(finding_id, payload)


@router.post("/findings/{finding_id}/submit", response_model=Finding)
def submit_finding(finding_id: int, payload: dict = None):
    actor = ""
    if payload and isinstance(payload, dict):
        actor = payload.get("actor", "")
    with get_db() as db:
        row = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
        if not row:
            raise NotFoundError("finding", finding_id)
        validate_finding_fields(
            category=row["category"],
            description=row["description"],
            risk_level=row["risk_level"],
            reported_by=row["reported_by"],
        )
        old_status = row["finding_status"]
        new_status = transition_finding(old_status, "submitted")
        db.execute("UPDATE findings SET finding_status = ? WHERE id = ?", (new_status, finding_id))
        record_audit(db, "finding", finding_id, "submit", actor, {
            "from_status": old_status,
            "to_status": new_status,
            "actor": actor,
            "note": f"观察项提交：{old_status} → {new_status}",
        })
        row = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    return row_to_finding(row)


@router.post("/findings/{finding_id}/transition", response_model=Finding)
def transition_finding_status(finding_id: int, payload: dict):
    target = payload.get("target_status")
    actor = payload.get("actor", "")
    note = payload.get("note", "")
    if not target:
        raise ValidationError("target_status is required")
    with get_db() as db:
        row = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
        if not row:
            raise NotFoundError("finding", finding_id)
        old_status = row["finding_status"]
        new_status = transition_finding(old_status, target)
        db.execute("UPDATE findings SET finding_status = ? WHERE id = ?", (new_status, finding_id))
        record_audit(db, "finding", finding_id, "status_change", actor, {
            "from_status": old_status,
            "to_status": new_status,
            "actor": actor,
            "note": note or f"状态流转：{old_status} → {new_status}",
        })
        row = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    return row_to_finding(row)


@router.get("/findings/{finding_id}/timeline")
def get_finding_timeline(finding_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
        if not row:
            raise NotFoundError("finding", finding_id)
        events = db.execute(
            "SELECT * FROM audit_events WHERE entity_type = 'finding' AND entity_id = ? ORDER BY created_at ASC",
            (finding_id,),
        ).fetchall()
        reviews = db.execute(
            "SELECT * FROM reviews WHERE finding_id = ? ORDER BY reviewed_at ASC",
            (finding_id,),
        ).fetchall()
        attachments = db.execute(
            "SELECT * FROM attachments WHERE linked_finding_id = ? ORDER BY id ASC",
            (finding_id,),
        ).fetchall()
    timeline = []
    timeline.append({
        "type": "finding_created",
        "action": "create_draft",
        "actor": row["reported_by"],
        "details": {
            "category": row["category"],
            "risk_level": row["risk_level"],
            "description": row["description"],
            "note": "观察项创建",
        },
        "timestamp": row["reported_at"],
    })
    for e in events:
        timeline.append({
            "type": "audit",
            "action": e["action"],
            "actor": e["actor"],
            "details": json.loads(e["details"]),
            "timestamp": e["created_at"],
        })
    for a in attachments:
        timeline.append({
            "type": "attachment",
            "action": "attachment_registered",
            "actor": "",
            "details": {
                "file_name": a["file_name"],
                "file_type": a["file_type"],
                "storage_note": a["storage_note"],
                "attachment_id": a["id"],
                "note": "附件登记",
            },
            "timestamp": a["created_at"],
        })
    for r in reviews:
        timeline.append({
            "type": "review",
            "action": "review",
            "actor": r["reviewer_name"],
            "details": {
                "conclusion": r["conclusion"],
                "comment": r["comment"],
                "note": "复核结论",
            },
            "timestamp": r["reviewed_at"],
        })
    timeline = [t for t in timeline if t.get("timestamp")]
    timeline.sort(key=lambda x: (x["timestamp"], x["type"] != "finding_created"))
    return {"finding_id": finding_id, "timeline": timeline}
