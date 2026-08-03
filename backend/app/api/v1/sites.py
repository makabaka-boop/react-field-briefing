from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.all_models import Attachment, AuditEvent, Finding, Project, Review, Site
from app.schemas.common import TimelineEvent
from app.schemas.site import Site as SiteSchema, SiteCreate, SiteUpdate
from app.services import audit_service

router = APIRouter(prefix="/sites", tags=["sites"])


@router.post("", response_model=SiteSchema, status_code=201)
def create_site(payload: SiteCreate, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    if not project:
        raise NotFoundError("Project not found", {"project_id": payload.project_id})
    site = Site(
        site_code=payload.site_code,
        site_name=payload.site_name,
        address_text=payload.address_text or "",
        region=payload.region or "",
        project_id=payload.project_id,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    audit_service.record(db, "site", site.id, "created", metadata={"project_id": project.id})
    db.commit()
    return site


@router.get("", response_model=list[SiteSchema])
def list_sites(
    project_id: int | None = Query(None),
    region: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Site)
    if project_id is not None:
        q = q.filter(Site.project_id == project_id)
    if region:
        q = q.filter(Site.region == region)
    return q.order_by(Site.id.asc()).all()


@router.get("/{site_id}", response_model=SiteSchema)
def get_site(site_id: int, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise NotFoundError("Site not found", {"site_id": site_id})
    return site


@router.patch("/{site_id}", response_model=SiteSchema)
def update_site(site_id: int, payload: SiteUpdate, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise NotFoundError("Site not found", {"site_id": site_id})
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(site, key, value)
    audit_service.record(db, "site", site.id, "updated", metadata={"fields": list(data.keys())})
    db.commit()
    db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=204)
def delete_site(site_id: int, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise NotFoundError("Site not found", {"site_id": site_id})
    audit_service.record(db, "site", site.id, "deleted", metadata={"project_id": site.project_id})
    db.delete(site)
    db.commit()


@router.get("/{site_id}/timeline", response_model=list[TimelineEvent])
def site_timeline(site_id: int, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise NotFoundError("Site not found", {"site_id": site_id})

    findings = db.query(Finding).filter(Finding.site_id == site_id).all()
    finding_ids = [f.id for f in findings]

    events: list[TimelineEvent] = []

    site_audit = (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_type == "site", AuditEvent.entity_id == site_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    for e in site_audit:
        note = (e.event_metadata or {}).get("note", "")
        events.append(
            TimelineEvent(
                event_type="audit_event",
                event_id=e.id,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                occurred_at=e.created_at.isoformat(),
                actor=e.actor,
                summary=f"[{e.action}] {note}".strip(),
                details={
                    "action": e.action,
                    "from_status": e.from_status,
                    "to_status": e.to_status,
                    "metadata": e.event_metadata or {},
                },
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
                summary=f"[{f.risk_level}] {f.category}: {f.description[:120]}",
                details={
                    "finding_status": f.finding_status,
                    "risk_level": f.risk_level,
                    "category": f.category,
                },
            )
        )

    if finding_ids:
        for att in (
            db.query(Attachment)
            .filter(Attachment.linked_finding_id.in_(finding_ids))
            .all()
        ):
            att_audit = (
                db.query(AuditEvent)
                .filter(
                    AuditEvent.entity_type == "attachment",
                    AuditEvent.entity_id == att.id,
                    AuditEvent.action == "registered",
                )
                .first()
            )
            events.append(
                TimelineEvent(
                    event_type="attachment_registered",
                    event_id=att.id,
                    entity_type="attachment",
                    entity_id=att.id,
                    occurred_at=(att_audit.created_at.isoformat() if att_audit else ""),
                    actor=(att_audit.actor if att_audit else "system"),
                    summary=f"Attachment registered: {att.file_name}",
                    details={
                        "file_name": att.file_name,
                        "file_type": att.file_type,
                        "storage_note": att.storage_note,
                        "linked_finding_id": att.linked_finding_id,
                    },
                )
            )

        for r in (
            db.query(Review)
            .filter(Review.finding_id.in_(finding_ids))
            .all()
        ):
            events.append(
                TimelineEvent(
                    event_type="review_concluded",
                    event_id=r.id,
                    entity_type="review",
                    entity_id=r.id,
                    occurred_at=r.reviewed_at.isoformat(),
                    actor=r.reviewer_name,
                    summary=f"Review {r.conclusion} by {r.reviewer_name}",
                    details={
                        "conclusion": r.conclusion,
                        "comment": r.comment,
                        "finding_id": r.finding_id,
                    },
                )
            )

        finding_audits = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.entity_type == "finding",
                AuditEvent.entity_id.in_(finding_ids),
            )
            .all()
        )
        for e in finding_audits:
            note = (e.event_metadata or {}).get("note", "")
            transition = (
                f"{e.from_status} → {e.to_status}"
                if e.from_status or e.to_status
                else e.action
            )
            events.append(
                TimelineEvent(
                    event_type="audit_event",
                    event_id=e.id,
                    entity_type=e.entity_type,
                    entity_id=e.entity_id,
                    occurred_at=e.created_at.isoformat(),
                    actor=e.actor,
                    summary=f"Finding #{e.entity_id} {e.action} ({transition}) {('- ' + note) if note else ''}".strip(),
                    details={
                        "action": e.action,
                        "from_status": e.from_status,
                        "to_status": e.to_status,
                        "metadata": e.event_metadata or {},
                    },
                )
            )

    events.sort(key=lambda x: x.occurred_at or "", reverse=True)
    return events
