from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import NotFoundError, ValidationError
from app.core.state_machine import StatusMachine
from app.models.all_models import Finding, Site
from app.schemas.finding import (
    Finding as FindingSchema,
    FindingDraftCreate,
    FindingDraftUpdate,
    FindingStatusUpdate,
    FindingSubmit,
)
from app.services import audit_service

router = APIRouter(prefix="/findings", tags=["findings"])

REQUIRED_FIELDS = ("category", "description", "risk_level", "reported_by")


def _validate_required(finding: Finding) -> None:
    missing = [f for f in REQUIRED_FIELDS if not (getattr(finding, f, None) or "").strip()]
    if finding.risk_level not in settings.RISK_LEVELS:
        missing.append("risk_level")
    if missing:
        raise ValidationError(
            "Finding has missing or invalid fields and cannot be submitted.",
            {"missing_fields": sorted(set(missing))},
        )


@router.post("/draft", response_model=FindingSchema, status_code=201)
def save_draft(payload: FindingDraftCreate, db: Session = Depends(get_db)):
    site = db.get(Site, payload.site_id)
    if not site:
        raise NotFoundError("Site not found", {"site_id": payload.site_id})
    finding = Finding(
        site_id=payload.site_id,
        category=payload.category.strip(),
        description=payload.description.strip(),
        risk_level=payload.risk_level,
        finding_status="draft",
        reported_by=payload.reported_by.strip(),
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    audit_service.record(
        db, "finding", finding.id, "draft_saved",
        actor=finding.reported_by,
        metadata={"note": "Draft created with all required fields populated."},
    )
    db.commit()
    return finding


@router.patch("/{finding_id}/draft", response_model=FindingSchema)
def update_draft(finding_id: int, payload: FindingDraftUpdate, db: Session = Depends(get_db)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise NotFoundError("Finding not found", {"finding_id": finding_id})
    if finding.finding_status != "draft":
        raise ValidationError(
            "Only draft findings can be edited",
            {"finding_status": finding.finding_status},
        )
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValidationError(
                    f"Field '{key}' must not be empty.",
                    {"field": key},
                )
        setattr(finding, key, value)
    if finding.risk_level not in settings.RISK_LEVELS:
        raise ValidationError(
            "Invalid risk level.",
            {"risk_level": finding.risk_level, "allowed": list(settings.RISK_LEVELS)},
        )
    audit_service.record(
        db, "finding", finding.id, "draft_updated",
        actor=finding.reported_by or "system",
        metadata={"fields": list(data.keys()), "note": "Draft fields updated."},
    )
    db.commit()
    db.refresh(finding)
    return finding


@router.post("/{finding_id}/submit", response_model=FindingSchema)
def submit_finding(finding_id: int, payload: FindingSubmit, db: Session = Depends(get_db)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise NotFoundError("Finding not found", {"finding_id": finding_id})
    _validate_required(finding)
    old = finding.finding_status
    try:
        StatusMachine.validate(old, "submitted", kind="finding")
    except Exception as exc:
        raise ValidationError(str(exc), {"from": old, "to": "submitted"})
    finding.finding_status = "submitted"
    actor = payload.actor.strip()
    if actor:
        finding.reported_by = actor
    audit_service.record(
        db, "finding", finding.id, "submitted",
        actor=actor or finding.reported_by,
        from_status=old, to_status="submitted",
        metadata={"note": payload.note or "Finding submitted for review."},
    )
    db.commit()
    db.refresh(finding)
    return finding


@router.patch("/{finding_id}/status", response_model=FindingSchema)
def update_status(finding_id: int, payload: FindingStatusUpdate, db: Session = Depends(get_db)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise NotFoundError("Finding not found", {"finding_id": finding_id})
    if payload.status not in settings.ALLOWED_STATUSES:
        raise ValidationError(
            "Invalid target status.",
            {"status": payload.status, "allowed": list(settings.ALLOWED_STATUSES)},
        )
    old = finding.finding_status
    try:
        StatusMachine.validate(old, payload.status, kind="finding")
    except Exception as exc:
        raise ValidationError(str(exc), {"from": old, "to": payload.status})

    note = (payload.note or "").strip() or _default_note(old, payload.status)
    finding.finding_status = payload.status
    audit_service.record(
        db, "finding", finding.id, "status_changed",
        actor=payload.actor.strip(),
        from_status=old, to_status=payload.status,
        metadata={"note": note},
    )
    db.commit()
    db.refresh(finding)
    return finding


def _default_note(old: str, new: str) -> str:
    if old == "submitted" and new == "reviewing":
        return "Finding entered review."
    if new == "accepted":
        return "Finding accepted after review."
    if new == "rejected":
        return "Finding rejected and returned for revision."
    if new == "submitted":
        return "Finding resubmitted."
    if new == "draft":
        return "Finding returned to draft for revision."
    if new == "archived":
        return "Finding archived."
    return f"Status changed from {old} to {new}."


@router.get("", response_model=list[FindingSchema])
def list_findings(
    site_id: int | None = Query(None),
    status: str | None = Query(None),
    risk_level: str | None = Query(None),
    project_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Finding)
    if site_id is not None:
        q = q.filter(Finding.site_id == site_id)
    if status:
        q = q.filter(Finding.finding_status == status)
    if risk_level:
        if risk_level not in settings.RISK_LEVELS:
            raise ValidationError(
                "Invalid risk level filter.",
                {"risk_level": risk_level, "allowed": list(settings.RISK_LEVELS)},
            )
        q = q.filter(Finding.risk_level == risk_level)
    if project_id is not None:
        q = q.join(Site, Site.id == Finding.site_id).filter(Site.project_id == project_id)
    return q.order_by(Finding.reported_at.desc()).all()


@router.get("/{finding_id}", response_model=FindingSchema)
def get_finding(finding_id: int, db: Session = Depends(get_db)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise NotFoundError("Finding not found", {"finding_id": finding_id})
    return finding
