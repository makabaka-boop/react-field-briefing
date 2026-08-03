from fastapi import APIRouter, Query
from typing import List, Optional
import json
from ..database import get_db
from ..schemas import SiteCreate, SiteUpdate, Site
from ..errors import NotFoundError, ConflictError
from ..audit import record_audit

router = APIRouter()


def row_to_site(row):
    return {
        "id": row["id"],
        "site_code": row["site_code"],
        "site_name": row["site_name"],
        "address_text": row["address_text"],
        "region": row["region"],
        "project_id": row["project_id"],
    }


@router.post("/sites", response_model=Site)
def create_site(payload: SiteCreate):
    with get_db() as db:
        project = db.execute("SELECT id FROM projects WHERE id = ?", (payload.project_id,)).fetchone()
        if not project:
            raise NotFoundError("project", payload.project_id)
        existing = db.execute("SELECT id FROM sites WHERE site_code = ?", (payload.site_code,)).fetchone()
        if existing:
            raise ConflictError(f"Site code {payload.site_code} already exists", {"site_code": payload.site_code})
        cur = db.execute(
            "INSERT INTO sites (site_code, site_name, address_text, region, project_id) VALUES (?, ?, ?, ?, ?)",
            (payload.site_code, payload.site_name, payload.address_text, payload.region, payload.project_id),
        )
        sid = cur.lastrowid
        record_audit(db, "site", sid, "create", "", {"site_code": payload.site_code})
        row = db.execute("SELECT * FROM sites WHERE id = ?", (sid,)).fetchone()
    return row_to_site(row)


@router.get("/sites", response_model=List[Site])
def list_sites(
    project_id: Optional[int] = Query(None),
    region: Optional[str] = Query(None),
):
    with get_db() as db:
        sql = "SELECT * FROM sites WHERE 1=1"
        params = []
        if project_id is not None:
            sql += " AND project_id = ?"
            params.append(project_id)
        if region:
            sql += " AND region = ?"
            params.append(region)
        sql += " ORDER BY id"
        rows = db.execute(sql, params).fetchall()
    return [row_to_site(r) for r in rows]


@router.get("/sites/{site_id}", response_model=Site)
def get_site(site_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
    if not row:
        raise NotFoundError("site", site_id)
    return row_to_site(row)


@router.patch("/sites/{site_id}", response_model=Site)
def update_site(site_id: int, payload: SiteUpdate):
    with get_db() as db:
        row = db.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
        if not row:
            raise NotFoundError("site", site_id)
        updates = []
        params = []
        if payload.site_name is not None:
            updates.append("site_name = ?")
            params.append(payload.site_name)
        if payload.address_text is not None:
            updates.append("address_text = ?")
            params.append(payload.address_text)
        if payload.region is not None:
            updates.append("region = ?")
            params.append(payload.region)
        if updates:
            params.append(site_id)
            db.execute(f"UPDATE sites SET {', '.join(updates)} WHERE id = ?", params)
            record_audit(db, "site", site_id, "update", "", {})
        row = db.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
    return row_to_site(row)


@router.delete("/sites/{site_id}")
def delete_site(site_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
        if not row:
            raise NotFoundError("site", site_id)
        db.execute("DELETE FROM sites WHERE id = ?", (site_id,))
        record_audit(db, "site", site_id, "delete", "", {})
    return {"deleted": site_id}


@router.get("/sites/{site_id}/timeline")
def get_site_timeline(site_id: int):
    with get_db() as db:
        site = db.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
        if not site:
            raise NotFoundError("site", site_id)
        findings = db.execute(
            "SELECT * FROM findings WHERE site_id = ? ORDER BY reported_at ASC",
            (site_id,),
        ).fetchall()
        finding_ids = [f["id"] for f in findings]
        audit_events = []
        reviews = []
        attachments = []
        if finding_ids:
            placeholders = ",".join("?" * len(finding_ids))
            audit_events = db.execute(
                f"SELECT * FROM audit_events WHERE entity_type = 'finding' AND entity_id IN ({placeholders}) ORDER BY created_at ASC",
                finding_ids,
            ).fetchall()
            reviews = db.execute(
                f"SELECT * FROM reviews WHERE finding_id IN ({placeholders}) ORDER BY reviewed_at ASC",
                finding_ids,
            ).fetchall()
            attachments = db.execute(
                f"SELECT * FROM attachments WHERE linked_finding_id IN ({placeholders}) ORDER BY created_at ASC",
                finding_ids,
            ).fetchall()
        site_audit = db.execute(
            "SELECT * FROM audit_events WHERE entity_type = 'site' AND entity_id = ? ORDER BY created_at ASC",
            (site_id,),
        ).fetchall()

    timeline = []
    for s in site_audit:
        timeline.append({
            "type": "site_audit",
            "action": s["action"],
            "actor": s["actor"],
            "details": json.loads(s["details"]),
            "timestamp": s["created_at"],
            "finding_id": None,
        })
    for f in findings:
        timeline.append({
            "type": "finding_created",
            "action": "create_draft",
            "actor": f["reported_by"],
            "details": {
                "finding_id": f["id"],
                "category": f["category"],
                "risk_level": f["risk_level"],
                "description": f["description"],
                "note": "观察项创建",
            },
            "timestamp": f["reported_at"],
            "finding_id": f["id"],
        })
    for e in audit_events:
        timeline.append({
            "type": "audit",
            "action": e["action"],
            "actor": e["actor"],
            "details": json.loads(e["details"]),
            "timestamp": e["created_at"],
            "finding_id": e["entity_id"],
        })
    for a in attachments:
        timeline.append({
            "type": "attachment",
            "action": "attachment_registered",
            "actor": "",
            "details": {
                "attachment_id": a["id"],
                "file_name": a["file_name"],
                "file_type": a["file_type"],
                "storage_note": a["storage_note"],
                "note": "附件登记",
            },
            "timestamp": a["created_at"],
            "finding_id": a["linked_finding_id"],
        })
    for r in reviews:
        timeline.append({
            "type": "review",
            "action": "review",
            "actor": r["reviewer_name"],
            "details": {
                "review_id": r["id"],
                "conclusion": r["conclusion"],
                "comment": r["comment"],
                "note": "复核结论",
            },
            "timestamp": r["reviewed_at"],
            "finding_id": r["finding_id"],
        })
    timeline.sort(key=lambda x: x["timestamp"])
    return {
        "site_id": site_id,
        "site_code": site["site_code"],
        "site_name": site["site_name"],
        "timeline": timeline,
    }
