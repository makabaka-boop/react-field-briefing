from fastapi import APIRouter
import json
from ..database import get_db

router = APIRouter()


def _check_orphan_sites(db):
    rows = db.execute(
        """
        SELECT s.id, s.site_code, s.site_name, s.project_id
        FROM sites s
        LEFT JOIN projects p ON s.project_id = p.id
        WHERE p.id IS NULL
        """
    ).fetchall()
    issues = [
        {
            "site_id": r["id"],
            "site_code": r["site_code"],
            "site_name": r["site_name"],
            "project_id": r["project_id"],
            "message": f"Site {r['site_code']} references missing project_id={r['project_id']}",
        }
        for r in rows
    ]
    return {"check_code": "orphan_sites", "passed": len(issues) == 0, "issue_count": len(issues), "issues": issues}


def _check_orphan_findings(db):
    rows = db.execute(
        """
        SELECT f.id, f.site_id, f.category, f.description
        FROM findings f
        LEFT JOIN sites s ON f.site_id = s.id
        WHERE s.id IS NULL
        """
    ).fetchall()
    issues = [
        {
            "finding_id": r["id"],
            "site_id": r["site_id"],
            "category": r["category"],
            "message": f"Finding #{r['id']} references missing site_id={r['site_id']}",
        }
        for r in rows
    ]
    return {"check_code": "orphan_findings", "passed": len(issues) == 0, "issue_count": len(issues), "issues": issues}


def _check_status_audit_consistency(db):
    findings = db.execute(
        """
        SELECT id, finding_status, reported_at
        FROM findings
        """
    ).fetchall()
    issues = []
    for f in findings:
        events = db.execute(
            """
            SELECT action, details, created_at
            FROM audit_events
            WHERE entity_type = 'finding' AND entity_id = ?
              AND action IN ('submit', 'status_change', 'review')
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (f["id"],),
        ).fetchone()
        if events is None:
            continue
        try:
            details = json.loads(events["details"])
        except (json.JSONDecodeError, TypeError):
            details = {}
        recorded_to = details.get("to_status")
        if recorded_to and recorded_to != f["finding_status"]:
            issues.append({
                "finding_id": f["id"],
                "current_status": f["finding_status"],
                "last_audit_to_status": recorded_to,
                "last_audit_action": events["action"],
                "message": f"Finding #{f['id']} status={f['finding_status']} but last audit says to_status={recorded_to}",
            })
    return {"check_code": "status_audit_mismatch", "passed": len(issues) == 0, "issue_count": len(issues), "issues": issues}


def _check_orphan_attachments(db):
    rows = db.execute(
        """
        SELECT a.id, a.file_name, a.linked_finding_id
        FROM attachments a
        LEFT JOIN findings f ON a.linked_finding_id = f.id
        WHERE a.linked_finding_id IS NOT NULL AND f.id IS NULL
        """
    ).fetchall()
    issues = [
        {
            "attachment_id": r["id"],
            "file_name": r["file_name"],
            "linked_finding_id": r["linked_finding_id"],
            "message": f"Attachment {r['file_name']} references missing finding_id={r['linked_finding_id']}",
        }
        for r in rows
    ]
    return {"check_code": "orphan_attachments", "passed": len(issues) == 0, "issue_count": len(issues), "issues": issues}


def _check_duplicate_template_site_codes(db):
    templates = db.execute("SELECT id, template_name, site_items FROM templates").fetchall()
    issues = []
    for t in templates:
        try:
            items = json.loads(t["site_items"])
        except (json.JSONDecodeError, TypeError):
            issues.append({
                "template_id": t["id"],
                "template_name": t["template_name"],
                "message": f"Template {t['template_name']} has invalid site_items JSON",
            })
            continue
        if not isinstance(items, list):
            continue
        seen = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            code = (item.get("site_code") or "").strip()
            if not code:
                continue
            if code in seen:
                issues.append({
                    "template_id": t["id"],
                    "template_name": t["template_name"],
                    "site_code": code,
                    "message": f"Template {t['template_name']} has duplicate site_code={code}",
                })
            else:
                seen[code] = True
    return {"check_code": "duplicate_template_site_codes", "passed": len(issues) == 0, "issue_count": len(issues), "issues": issues}


def _check_risk_stats_consistency(db):
    issues = []
    projects = db.execute("SELECT id, project_code, project_name FROM projects").fetchall()
    for p in projects:
        pid = p["id"]
        overview_row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM findings f
            JOIN sites s ON f.site_id = s.id
            WHERE s.project_id = ? AND f.finding_status != 'archived'
            """,
            (pid,),
        ).fetchone()
        stats_total = overview_row["total"] if overview_row else 0

        site_rows = db.execute(
            """
            SELECT f.risk_level, COUNT(*) AS cnt
            FROM findings f
            JOIN sites s ON f.site_id = s.id
            WHERE s.project_id = ? AND f.finding_status != 'archived'
            GROUP BY f.risk_level
            """,
            (pid,),
        ).fetchall()
        detail_total = sum(r["cnt"] for r in site_rows)

        if stats_total != detail_total:
            issues.append({
                "project_id": pid,
                "project_code": p["project_code"],
                "stats_total": stats_total,
                "detail_total": detail_total,
                "message": f"Project {p['project_code']} risk stats total={stats_total} but detail sum={detail_total}",
            })

        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for r in site_rows:
            if r["risk_level"] in risk_counts:
                risk_counts[r["risk_level"]] = r["cnt"]
        risk_sum = sum(risk_counts.values())
        if risk_sum != stats_total:
            issues.append({
                "project_id": pid,
                "project_code": p["project_code"],
                "risk_sum": risk_sum,
                "stats_total": stats_total,
                "message": f"Project {p['project_code']} risk_counts sum={risk_sum} != total={stats_total}",
            })
    return {"check_code": "risk_stats_consistency", "passed": len(issues) == 0, "issue_count": len(issues), "issues": issues}


@router.get("/system/check")
def system_check():
    checks = []
    with get_db() as db:
        checks.append(_check_orphan_sites(db))
        checks.append(_check_orphan_findings(db))
        checks.append(_check_status_audit_consistency(db))
        checks.append(_check_orphan_attachments(db))
        checks.append(_check_duplicate_template_site_codes(db))
        checks.append(_check_risk_stats_consistency(db))

    total_issues = sum(c["issue_count"] for c in checks)
    all_passed = all(c["passed"] for c in checks)
    return {
        "all_passed": all_passed,
        "total_checks": len(checks),
        "passed_checks": sum(1 for c in checks if c["passed"]),
        "total_issues": total_issues,
        "checks": checks,
    }
