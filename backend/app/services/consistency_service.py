from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.all_models import (
    Attachment,
    AuditEvent,
    Finding,
    Project,
    Review,
    Site,
    SiteTemplate,
)
from app.services.risk_service import compute_project_risk_summary


def _check(name: str, description: str, issues: list[dict]) -> dict:
    return {
        "check_name": name,
        "description": description,
        "passed": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
    }


def orphan_sites(db: Session) -> dict:
    rows = (
        db.query(Site)
        .outerjoin(Project, Project.id == Site.project_id)
        .filter(Project.id.is_(None))
        .all()
    )
    issues = [
        {"site_id": s.id, "site_code": s.site_code, "project_id": s.project_id}
        for s in rows
    ]
    return _check(
        "orphan_sites",
        "Sites must reference an existing project.",
        issues,
    )


def orphan_findings(db: Session) -> dict:
    rows = (
        db.query(Finding)
        .outerjoin(Site, Site.id == Finding.site_id)
        .filter(Site.id.is_(None))
        .all()
    )
    issues = [
        {"finding_id": f.id, "site_id": f.site_id, "category": f.category}
        for f in rows
    ]
    return _check(
        "orphan_findings",
        "Findings must reference an existing site.",
        issues,
    )


def orphan_attachments(db: Session) -> dict:
    rows = (
        db.query(Attachment)
        .outerjoin(Finding, Finding.id == Attachment.linked_finding_id)
        .filter(Finding.id.is_(None))
        .all()
    )
    issues = [
        {
            "attachment_id": a.id,
            "file_name": a.file_name,
            "linked_finding_id": a.linked_finding_id,
        }
        for a in rows
    ]
    return _check(
        "orphan_attachments",
        "Attachments must reference an existing finding.",
        issues,
    )


def _last_status_event(db: Session, entity_type: str, entity_id: int):
    return (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == entity_type,
            AuditEvent.entity_id == entity_id,
            AuditEvent.to_status != "",
        )
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .first()
    )


def status_audit_drift(db: Session) -> dict:
    issues: list[dict] = []

    for finding in db.query(Finding).all():
        event = _last_status_event(db, "finding", finding.id)
        if event is None:
            if finding.finding_status != "draft":
                issues.append({
                    "entity_type": "finding",
                    "entity_id": finding.id,
                    "current_status": finding.finding_status,
                    "last_audit_to_status": None,
                    "reason": "non-draft finding has no status audit event",
                })
            continue
        if event.to_status != finding.finding_status:
            issues.append({
                "entity_type": "finding",
                "entity_id": finding.id,
                "current_status": finding.finding_status,
                "last_audit_to_status": event.to_status,
                "reason": "finding status does not match last audit event",
            })

    for project in db.query(Project).all():
        event = _last_status_event(db, "project", project.id)
        if event is None:
            if project.status != "draft":
                issues.append({
                    "entity_type": "project",
                    "entity_id": project.id,
                    "current_status": project.status,
                    "last_audit_to_status": None,
                    "reason": "non-draft project has no status audit event",
                })
            continue
        if event.to_status != project.status:
            issues.append({
                "entity_type": "project",
                "entity_id": project.id,
                "current_status": project.status,
                "last_audit_to_status": event.to_status,
                "reason": "project status does not match last audit event",
            })

    return _check(
        "status_audit_drift",
        "Project/finding status must match the latest audit status event.",
        issues,
    )


def template_duplicate_site_codes(db: Session) -> dict:
    issues: list[dict] = []
    for tpl in db.query(SiteTemplate).all():
        seen: dict[str, int] = {}
        items = tpl.site_items if isinstance(tpl.site_items, list) else []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            code = str(item.get("site_code") or "").strip()
            if not code:
                continue
            if code in seen:
                issues.append({
                    "template_id": tpl.id,
                    "template_name": tpl.template_name,
                    "site_code": code,
                    "first_index": seen[code],
                    "duplicate_index": idx,
                })
            else:
                seen[code] = idx
    return _check(
        "template_duplicate_site_codes",
        "Template site_items must not contain duplicate site_code values.",
        issues,
    )


def overview_consistency(db: Session) -> dict:
    issues: list[dict] = []

    non_archived_total = (
        db.query(func.count(Finding.id))
        .filter(Finding.finding_status != "archived")
        .scalar()
    ) or 0
    unreviewed_total = (
        db.query(func.count(Finding.id))
        .filter(
            Finding.finding_status != "archived",
            Finding.finding_status.notin_(["accepted", "rejected"]),
        )
        .scalar()
    ) or 0
    rejected_total = (
        db.query(func.count(Finding.id))
        .filter(Finding.finding_status == "rejected")
        .scalar()
    ) or 0

    summed_total = 0
    summed_unreviewed = 0
    summed_rejected = 0
    for project in db.query(Project).all():
        summary = compute_project_risk_summary(db, project)
        summed_total += summary["total_findings"]
        summed_unreviewed += summary["unreviewed_count"]
        summed_rejected += summary["rejected_count"]

    for label, expected, actual in [
        ("total_findings", non_archived_total, summed_total),
        ("unreviewed_count", unreviewed_total, summed_unreviewed),
        ("rejected_count", rejected_total, summed_rejected),
    ]:
        if expected != actual:
            issues.append({
                "metric": label,
                "aggregated_value": actual,
                "expected_value": expected,
            })

    return _check(
        "overview_consistency",
        "Risk overview totals must equal the sum of per-project details (archived excluded).",
        issues,
    )


CHECKS = [
    orphan_sites,
    orphan_findings,
    status_audit_drift,
    orphan_attachments,
    template_duplicate_site_codes,
    overview_consistency,
]


def run_all_checks(db: Session) -> dict:
    results = [fn(db) for fn in CHECKS]
    total_issues = sum(r["issue_count"] for r in results)
    return {
        "passed": total_issues == 0,
        "total_checks": len(results),
        "failed_checks": sum(1 for r in results if not r["passed"]),
        "total_issues": total_issues,
        "checks": results,
    }
