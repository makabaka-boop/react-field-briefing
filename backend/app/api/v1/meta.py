from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.all_models import AuditEvent, Attachment, Finding, Review, Site
from app.schemas.audit import AuditEvent as AuditEventSchema
from app.schemas.common import (
    ConsistencyReport,
    RiskOverview,
    SiteRiskItem,
    TimelineEvent,
)
from app.services.consistency_service import run_all_checks

router = APIRouter(tags=["meta"])


@router.get("/consistency", response_model=ConsistencyReport)
def consistency_check(db: Session = Depends(get_db)):
    return run_all_checks(db)


@router.get("/audit", response_model=list[AuditEventSchema])
def list_audit(
    entity_type: str | None = Query(None),
    entity_id: int | None = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(AuditEvent)
    if entity_type:
        q = q.filter(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditEvent.entity_id == entity_id)
    return q.order_by(AuditEvent.created_at.desc()).limit(limit).all()


@router.get("/overview", response_model=RiskOverview)
def risk_overview(db: Session = Depends(get_db)):
    from app.models.all_models import Project, SiteTemplate  # noqa

    total_projects = db.query(Project).count()
    total_sites = db.query(Site).count()
    total_findings = db.query(Finding).count()

    by_risk = {level: 0 for level in ("low", "medium", "high", "critical")}
    by_status = {s: 0 for s in ("draft", "submitted", "reviewing", "accepted", "rejected", "archived")}
    by_region: dict[str, int] = {}

    for f in db.query(Finding).all():
        by_risk[f.risk_level] = by_risk.get(f.risk_level, 0) + 1
        by_status[f.finding_status] = by_status.get(f.finding_status, 0) + 1
    for s in db.query(Site).all():
        key = s.region or "unknown"
        by_region[key] = by_region.get(key, 0) + 1

    return RiskOverview(
        total_projects=total_projects,
        total_sites=total_sites,
        total_findings=total_findings,
        by_risk=by_risk,
        by_status=by_status,
        by_region=by_region,
    )


@router.get("/projects/{project_id}/site-risks", response_model=list[SiteRiskItem])
def project_site_risks(project_id: int, db: Session = Depends(get_db)):
    sites = db.query(Site).filter(Site.project_id == project_id).all()
    risk_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    result = []
    for site in sites:
        by_risk = {level: 0 for level in ("low", "medium", "high", "critical")}
        highest = "low"
        for f in site.findings:
            by_risk[f.risk_level] += 1
            if risk_rank.get(f.risk_level, 0) > risk_rank.get(highest, 0):
                highest = f.risk_level
        result.append(
            SiteRiskItem(
                site_id=site.id,
                site_code=site.site_code,
                site_name=site.site_name,
                region=site.region,
                total_findings=len(site.findings),
                by_risk=by_risk,
                highest_risk=highest,
            )
        )
    return result


@router.get("/projects/{project_id}/timeline", response_model=list[TimelineEvent])
def project_timeline(project_id: int, db: Session = Depends(get_db)):
    sites = db.query(Site).filter(Site.project_id == project_id).all()
    site_ids = [s.id for s in sites]
    if not site_ids:
        return []
    findings = db.query(Finding).filter(Finding.site_id.in_(site_ids)).all()
    finding_ids = [f.id for f in findings]

    site_audit = {
        e.entity_id: e
        for e in db.query(AuditEvent).filter(
            AuditEvent.entity_type == "site",
            AuditEvent.entity_id.in_(site_ids),
            AuditEvent.action == "created",
        ).all()
    }
    attachments = (
        db.query(Attachment).filter(Attachment.linked_finding_id.in_(finding_ids)).all()
        if finding_ids else []
    )
    att_ids = [a.id for a in attachments]
    att_audit = {
        e.entity_id: e
        for e in db.query(AuditEvent).filter(
            AuditEvent.entity_type == "attachment",
            AuditEvent.entity_id.in_(att_ids) if att_ids else False,
            AuditEvent.action == "registered",
        ).all()
    } if att_ids else {}

    events: list[TimelineEvent] = []

    for s in sites:
        ts = site_audit.get(s.id).created_at.isoformat() if s.id in site_audit else ""
        events.append(
            TimelineEvent(
                event_type="site_created",
                event_id=s.id,
                entity_type="site",
                entity_id=s.id,
                occurred_at=ts,
                actor=site_audit.get(s.id).actor if s.id in site_audit else "system",
                summary=f"Site created: {s.site_code} - {s.site_name}",
                details={"site_code": s.site_code, "region": s.region},
            )
        )
    for f in findings:
        events.append(
            TimelineEvent(
                event_type="finding_reported",
                event_id=f.id,
                entity_type="finding",
                entity_id=f.id,
                occurred_at=f.reported_at.isoformat(),
                actor=f.reported_by,
                summary=f"[{f.risk_level}] {f.category}: {f.description[:80]}",
                details={
                    "site_id": f.site_id,
                    "category": f.category,
                    "risk_level": f.risk_level,
                    "finding_status": f.finding_status,
                },
            )
        )
    for att in attachments:
        ts = att_audit.get(att.id).created_at.isoformat() if att.id in att_audit else ""
        events.append(
            TimelineEvent(
                event_type="attachment_registered",
                event_id=att.id,
                entity_type="attachment",
                entity_id=att.id,
                occurred_at=ts,
                actor=att_audit.get(att.id).actor if att.id in att_audit else "system",
                summary=f"Attachment: {att.file_name}",
                details={"file_type": att.file_type, "linked_finding_id": att.linked_finding_id},
            )
        )
    if finding_ids:
        for r in db.query(Review).filter(Review.finding_id.in_(finding_ids)).all():
            events.append(
                TimelineEvent(
                    event_type="review_concluded",
                    event_id=r.id,
                    entity_type="review",
                    entity_id=r.id,
                    occurred_at=r.reviewed_at.isoformat(),
                    actor=r.reviewer_name,
                    summary=f"Review {r.conclusion} by {r.reviewer_name}",
                    details={"conclusion": r.conclusion, "comment": r.comment, "finding_id": r.finding_id},
                )
            )

    events.sort(key=lambda e: e.occurred_at or "", reverse=True)
    return events
