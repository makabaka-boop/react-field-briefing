from fastapi import APIRouter, Query
from typing import Optional
from ..database import get_db
from ..errors import NotFoundError

router = APIRouter()

RISK_ORDER = ["critical", "high", "medium", "low"]
UNREVIEWED_STATUSES = ("draft", "submitted", "reviewing")


def _empty_risk_counts():
    return {"low": 0, "medium": 0, "high": 0, "critical": 0}


def _empty_status_counts():
    return {"draft": 0, "submitted": 0, "reviewing": 0, "accepted": 0, "rejected": 0, "archived": 0}


def _compute_site_stats(db, site_id):
    row = db.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN finding_status IN (?, ?, ?) THEN 1 ELSE 0 END) AS unreviewed,
            SUM(CASE WHEN finding_status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN finding_status = 'archived' THEN 1 ELSE 0 END) AS archived,
            MAX(reported_at) AS last_updated
        FROM findings
        WHERE site_id = ? AND finding_status != 'archived'
        """,
        (*UNREVIEWED_STATUSES, site_id),
    ).fetchone()

    risk_rows = db.execute(
        """
        SELECT risk_level, COUNT(*) AS cnt
        FROM findings
        WHERE site_id = ? AND finding_status != 'archived'
        GROUP BY risk_level
        """,
        (site_id,),
    ).fetchall()

    risk_counts = _empty_risk_counts()
    for rr in risk_rows:
        if rr["risk_level"] in risk_counts:
            risk_counts[rr["risk_level"]] = rr["cnt"]

    max_risk = "none"
    for level in RISK_ORDER:
        if risk_counts[level] > 0:
            max_risk = level
            break

    return {
        "total_findings": row["total"] or 0,
        "unreviewed_count": row["unreviewed"] or 0,
        "rejected_count": row["rejected"] or 0,
        "archived_count": row["archived"] or 0,
        "risk_counts": risk_counts,
        "max_risk_level": max_risk,
        "last_updated": row["last_updated"],
    }


@router.get("/overview/risk")
def risk_overview(project_id: Optional[int] = Query(None)):
    with get_db() as db:
        sql = """
            SELECT f.risk_level, f.finding_status, COUNT(*) as cnt
            FROM findings f
            JOIN sites s ON f.site_id = s.id
            WHERE f.finding_status != 'archived'
        """
        params = []
        if project_id is not None:
            sql += " AND s.project_id = ?"
            params.append(project_id)
        sql += " GROUP BY f.risk_level, f.finding_status"
        rows = db.execute(sql, params).fetchall()

        risk_counts = _empty_risk_counts()
        status_counts = _empty_status_counts()
        for r in rows:
            rl = r["risk_level"]
            st = r["finding_status"]
            if rl in risk_counts:
                risk_counts[rl] += r["cnt"]
            if st in status_counts:
                status_counts[st] += r["cnt"]

        total_findings = sum(risk_counts.values())

        if project_id is not None:
            project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not project:
                raise NotFoundError("project", project_id)
            site_count = db.execute("SELECT COUNT(*) as cnt FROM sites WHERE project_id = ?", (project_id,)).fetchone()["cnt"]
        else:
            site_count = db.execute("SELECT COUNT(*) as cnt FROM sites").fetchone()["cnt"]

    return {
        "project_id": project_id,
        "total_findings": total_findings,
        "total_sites": site_count,
        "risk_counts": risk_counts,
        "status_counts": status_counts,
    }


@router.get("/projects/{project_id}/sites-risk")
def project_sites_risk(project_id: int):
    with get_db() as db:
        project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise NotFoundError("project", project_id)
        sites = db.execute(
            "SELECT * FROM sites WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
        result = []
        for site in sites:
            stats = _compute_site_stats(db, site["id"])
            result.append({
                "site_id": site["id"],
                "site_code": site["site_code"],
                "site_name": site["site_name"],
                "region": site["region"],
                "address_text": site["address_text"],
                **stats,
            })

        project_stats = {
            "total_findings": sum(s["total_findings"] for s in result),
            "unreviewed_count": sum(s["unreviewed_count"] for s in result),
            "rejected_count": sum(s["rejected_count"] for s in result),
            "archived_count": sum(s["archived_count"] for s in result),
        }
    return {
        "project_id": project_id,
        "project_code": project["project_code"],
        "project_name": project["project_name"],
        "sites": result,
        "summary": project_stats,
    }
