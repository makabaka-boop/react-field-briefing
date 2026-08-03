from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.all_models import AuditEvent, Finding, Project, Review, Site

RISK_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
REVIEWED_STATUSES = ("accepted", "rejected")
NON_ARCHIVED = (
    "draft",
    "submitted",
    "reviewing",
    "accepted",
    "rejected",
)


def max_risk(current: str, candidate: Optional[str]) -> str:
    if candidate and RISK_RANK.get(candidate, 0) > RISK_RANK.get(current, 0):
        return candidate
    return current


def _latest_event_time(
    db: Session, entity_type: str, entity_id: int
) -> Optional[datetime]:
    row = db.execute(
        select(AuditEvent.created_at)
        .where(AuditEvent.entity_type == entity_type, AuditEvent.entity_id == entity_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    ).first()
    return row[0] if row else None


def compute_site_summary(db: Session, site: Site) -> dict:
    findings = (
        db.query(Finding)
        .filter(Finding.site_id == site.id, Finding.finding_status != "archived")
        .all()
    )
    total = len(findings)
    unreviewed = sum(1 for f in findings if f.finding_status not in REVIEWED_STATUSES)
    rejected = sum(1 for f in findings if f.finding_status == "rejected")

    highest = "none"
    latest: Optional[datetime] = None
    for f in findings:
        highest = max_risk(highest, f.risk_level)
        if f.reported_at and (latest is None or f.reported_at > latest):
            latest = f.reported_at

    for f in findings:
        review_ts = (
            db.query(Review.reviewed_at)
            .filter(Review.finding_id == f.id)
            .order_by(Review.reviewed_at.desc())
            .first()
        )
        if review_ts and review_ts[0] and (latest is None or review_ts[0] > latest):
            latest = review_ts[0]

    audit_ts = _latest_event_time(db, "site", site.id)
    if audit_ts and (latest is None or audit_ts > latest):
        latest = audit_ts

    return {
        "site_id": site.id,
        "site_code": site.site_code,
        "site_name": site.site_name,
        "region": site.region or "",
        "total_findings": total,
        "unreviewed_count": unreviewed,
        "rejected_count": rejected,
        "highest_risk": highest,
        "last_updated_at": latest.isoformat() if latest else None,
    }


def compute_project_risk_summary(db: Session, project: Project) -> dict:
    sites = db.query(Site).filter(Site.project_id == project.id).all()
    site_summaries = [compute_site_summary(db, s) for s in sites]

    total_findings = sum(s["total_findings"] for s in site_summaries)
    unreviewed = sum(s["unreviewed_count"] for s in site_summaries)
    rejected = sum(s["rejected_count"] for s in site_summaries)
    highest = "none"
    latest: Optional[datetime] = None
    for s in site_summaries:
        highest = max_risk(highest, s["highest_risk"])
        if s["last_updated_at"]:
            ts = datetime.fromisoformat(s["last_updated_at"])
            if latest is None or ts > latest:
                latest = ts

    project_audit = _latest_event_time(db, "project", project.id)
    if project_audit and (latest is None or project_audit > latest):
        latest = project_audit

    return {
        "project_id": project.id,
        "project_code": project.project_code,
        "project_name": project.project_name,
        "total_sites": len(sites),
        "total_findings": total_findings,
        "unreviewed_count": unreviewed,
        "rejected_count": rejected,
        "highest_risk": highest,
        "last_updated_at": latest.isoformat() if latest else None,
        "sites": site_summaries,
    }
