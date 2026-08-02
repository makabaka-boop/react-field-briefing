from fastapi import APIRouter, Query
from typing import List, Optional
import json
from ..database import get_db
from ..schemas import ProjectCreate, ProjectUpdate, Project, ProjectFromTemplate
from ..errors import NotFoundError, ConflictError, ValidationError
from ..state_machine import validate_status, transition_project
from ..audit import record_audit

router = APIRouter()

RISK_ORDER = ["critical", "high", "medium", "low"]
UNREVIEWED_STATUSES = ("draft", "submitted", "reviewing")


def row_to_project(row):
    return {
        "id": row["id"],
        "project_code": row["project_code"],
        "project_name": row["project_name"],
        "owner_name": row["owner_name"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def _project_risk_summary(db, project_id):
    row = db.execute(
        """
        SELECT
            COUNT(f.id) AS total_findings,
            SUM(CASE WHEN f.finding_status IN (?, ?, ?) THEN 1 ELSE 0 END) AS unreviewed_count,
            SUM(CASE WHEN f.finding_status = 'rejected' THEN 1 ELSE 0 END) AS rejected_count,
            MAX(f.reported_at) AS last_updated
        FROM findings f
        JOIN sites s ON f.site_id = s.id
        WHERE s.project_id = ? AND f.finding_status != 'archived'
        """,
        (*UNREVIEWED_STATUSES, project_id),
    ).fetchone()

    risk_rows = db.execute(
        """
        SELECT f.risk_level, COUNT(*) AS cnt
        FROM findings f
        JOIN sites s ON f.site_id = s.id
        WHERE s.project_id = ? AND f.finding_status != 'archived'
        GROUP BY f.risk_level
        """,
        (project_id,),
    ).fetchall()
    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for rr in risk_rows:
        if rr["risk_level"] in risk_counts:
            risk_counts[rr["risk_level"]] = rr["cnt"]
    max_risk = "none"
    for level in RISK_ORDER:
        if risk_counts[level] > 0:
            max_risk = level
            break

    return {
        "total_findings": row["total_findings"] or 0,
        "unreviewed_count": row["unreviewed_count"] or 0,
        "rejected_count": row["rejected_count"] or 0,
        "max_risk_level": max_risk,
        "last_updated": row["last_updated"],
        "risk_counts": risk_counts,
    }


@router.post("/projects", response_model=Project)
def create_project(payload: ProjectCreate):
    validate_status(payload.status)
    with get_db() as db:
        existing = db.execute("SELECT id FROM projects WHERE project_code = ?", (payload.project_code,)).fetchone()
        if existing:
            raise ConflictError(f"Project code {payload.project_code} already exists", {"project_code": payload.project_code})
        cur = db.execute(
            "INSERT INTO projects (project_code, project_name, owner_name, status) VALUES (?, ?, ?, ?)",
            (payload.project_code, payload.project_name, payload.owner_name, payload.status),
        )
        pid = cur.lastrowid
        record_audit(db, "project", pid, "create", payload.owner_name, {"project_code": payload.project_code})
        row = db.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    return row_to_project(row)


@router.get("/projects")
def list_projects(
    status: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    max_risk_level: Optional[str] = Query(None),
):
    with get_db() as db:
        sql = "SELECT DISTINCT p.* FROM projects p"
        params = []
        conditions = []

        if status:
            validate_status(status)
            conditions.append("p.status = ?")
            params.append(status)

        if region:
            sql += " JOIN sites s ON s.project_id = p.id"
            conditions.append("s.region = ?")
            params.append(region)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY p.created_at DESC"
        rows = db.execute(sql, params).fetchall()

        result = []
        for r in rows:
            proj = row_to_project(r)
            summary = _project_risk_summary(db, r["id"])
            if max_risk_level:
                if summary["max_risk_level"] != max_risk_level:
                    continue
            proj["risk_summary"] = summary
            result.append(proj)
    return result


@router.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        raise NotFoundError("project", project_id)
    return row_to_project(row)


@router.patch("/projects/{project_id}", response_model=Project)
def update_project(project_id: int, payload: ProjectUpdate):
    with get_db() as db:
        row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise NotFoundError("project", project_id)
        updates = []
        params = []
        if payload.project_name is not None:
            updates.append("project_name = ?")
            params.append(payload.project_name)
        if payload.owner_name is not None:
            updates.append("owner_name = ?")
            params.append(payload.owner_name)
        if payload.status is not None:
            validate_status(payload.status)
            transition_project(row["status"], payload.status)
            updates.append("status = ?")
            params.append(payload.status)
            record_audit(db, "project", project_id, "status_change", payload.owner_name or "", {
                "from": row["status"], "to": payload.status
            })
        if updates:
            params.append(project_id)
            db.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", params)
        row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row_to_project(row)


@router.post("/projects/{project_id}/transition", response_model=Project)
def transition_project_status(project_id: int, payload: dict):
    target = payload.get("target_status")
    actor = payload.get("actor", "")
    if not target:
        raise ValidationError("target_status is required")
    with get_db() as db:
        row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise NotFoundError("project", project_id)
        new_status = transition_project(row["status"], target)
        db.execute("UPDATE projects SET status = ? WHERE id = ?", (new_status, project_id))
        record_audit(db, "project", project_id, "status_change", actor, {
            "from": row["status"], "to": new_status
        })
        row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row_to_project(row)


def _validate_site_items(site_items, default_region):
    if not isinstance(site_items, list):
        raise ValidationError("site_items must be an array", {"field": "site_items"})
    seen_codes = set()
    validated = []
    for idx, item in enumerate(site_items):
        if not isinstance(item, dict):
            raise ValidationError(f"site_items[{idx}] must be an object", {"index": idx})
        code = (item.get("site_code") or "").strip()
        name = (item.get("site_name") or "").strip()
        if not code:
            raise ValidationError(f"site_items[{idx}].site_code is required", {"index": idx, "field": "site_code"})
        if not name:
            raise ValidationError(f"site_items[{idx}].site_name is required", {"index": idx, "field": "site_name"})
        if code in seen_codes:
            raise ConflictError(
                f"Duplicate site_code within template: {code}",
                {"site_code": code, "index": idx},
            )
        seen_codes.add(code)
        validated.append({
            "site_code": code,
            "site_name": name,
            "address_text": (item.get("address_text") or "").strip(),
            "region": (item.get("region") or default_region or "").strip(),
        })
    return validated


@router.post("/projects/from-template")
def create_project_from_template(payload: ProjectFromTemplate):
    validate_status(payload.status)
    with get_db() as db:
        try:
            existing = db.execute("SELECT id FROM projects WHERE project_code = ?", (payload.project_code,)).fetchone()
            if existing:
                raise ConflictError(
                    f"Project code {payload.project_code} already exists",
                    {"project_code": payload.project_code},
                )
            tpl = db.execute("SELECT * FROM templates WHERE id = ?", (payload.template_id,)).fetchone()
            if not tpl:
                raise NotFoundError("template", payload.template_id)

            try:
                raw_items = json.loads(tpl["site_items"])
            except (json.JSONDecodeError, TypeError):
                raise ValidationError("template site_items is not valid JSON", {"template_id": payload.template_id})

            site_items = _validate_site_items(raw_items, tpl["default_region"])

            cur = db.execute(
                "INSERT INTO projects (project_code, project_name, owner_name, status) VALUES (?, ?, ?, ?)",
                (payload.project_code, payload.project_name, payload.owner_name, payload.status),
            )
            pid = cur.lastrowid

            inserted_sites = []
            for item in site_items:
                dup = db.execute(
                    "SELECT id FROM sites WHERE site_code = ?",
                    (item["site_code"],),
                ).fetchone()
                if dup:
                    raise ConflictError(
                        f"Site code {item['site_code']} already exists",
                        {"site_code": item["site_code"]},
                    )
                db.execute(
                    "INSERT INTO sites (site_code, site_name, address_text, region, project_id) VALUES (?, ?, ?, ?, ?)",
                    (
                        item["site_code"],
                        item["site_name"],
                        item["address_text"],
                        item["region"],
                        pid,
                    ),
                )
                inserted_sites.append(item["site_code"])

            record_audit(db, "project", pid, "create_from_template", payload.owner_name, {
                "template_id": payload.template_id,
                "template_name": tpl["template_name"],
                "site_count": len(site_items),
                "site_codes": inserted_sites,
            })
            row = db.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
            result = row_to_project(row)
            result["sites_created"] = len(site_items)
            result["site_codes"] = inserted_sites
            result["template_name"] = tpl["template_name"]
            return result
        except (ConflictError, NotFoundError, ValidationError):
            raise
        except Exception:
            db.rollback()
            raise
