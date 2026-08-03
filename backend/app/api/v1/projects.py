from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.state_machine import StatusMachine
from app.models.all_models import Project, Site, SiteTemplate
from app.schemas.project import (
    Project as ProjectSchema,
    ProjectCreate,
    ProjectDetail,
    ProjectFromTemplate,
    ProjectListItem,
    ProjectRiskSummary,
    ProjectStatusUpdate,
)
from app.services import audit_service
from app.services.risk_service import RISK_RANK, compute_project_risk_summary

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_detail(project: Project) -> ProjectDetail:
    return ProjectDetail(
        id=project.id,
        project_code=project.project_code,
        project_name=project.project_name,
        owner_name=project.owner_name,
        status=project.status,
        created_at=project.created_at,
        site_count=len(project.sites),
    )


@router.post("", response_model=ProjectSchema, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        project_code=payload.project_code,
        project_name=payload.project_name,
        owner_name=payload.owner_name,
        status="draft",
    )
    db.add(project)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            f"Project code '{payload.project_code}' already exists.",
            {"project_code": payload.project_code},
        )
    db.refresh(project)
    audit_service.record(db, "project", project.id, "created", actor=payload.owner_name)
    db.commit()
    return project


def _project_list_item(db: Session, project: Project) -> ProjectListItem:
    summary = compute_project_risk_summary(db, project)
    return ProjectListItem(
        id=project.id,
        project_code=project.project_code,
        project_name=project.project_name,
        owner_name=project.owner_name,
        status=project.status,
        created_at=project.created_at,
        site_count=summary["total_sites"],
        highest_risk=summary["highest_risk"],
        total_findings=summary["total_findings"],
        unreviewed_count=summary["unreviewed_count"],
        rejected_count=summary["rejected_count"],
        last_updated_at=summary["last_updated_at"],
    )


@router.get("", response_model=list[ProjectListItem])
def list_projects(
    status: str | None = Query(None),
    region: str | None = Query(None),
    highest_risk: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Project)
    if status:
        q = q.filter(Project.status == status)

    if region:
        q = q.join(Site, Site.project_id == Project.id).filter(Site.region == region).distinct()

    projects = q.order_by(Project.created_at.desc()).all()
    items = [_project_list_item(db, p) for p in projects]

    if highest_risk:
        if highest_risk not in settings.RISK_LEVELS:
            raise ValidationError(
                "Invalid highest_risk filter.",
                {"highest_risk": highest_risk, "allowed": list(settings.RISK_LEVELS)},
            )
        threshold = RISK_RANK[highest_risk]
        items = [it for it in items if RISK_RANK.get(it.highest_risk, 0) >= threshold]

    return items


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project not found", {"project_id": project_id})
    return _to_detail(project)


@router.get("/{project_id}/risk-summary", response_model=ProjectRiskSummary)
def project_risk_summary(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project not found", {"project_id": project_id})
    return compute_project_risk_summary(db, project)


@router.patch("/{project_id}/status", response_model=ProjectSchema)
def update_project_status(
    project_id: int,
    payload: ProjectStatusUpdate,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project not found", {"project_id": project_id})
    old_status = project.status
    try:
        StatusMachine.validate(old_status, payload.status, kind="project")
    except Exception as exc:
        raise ValidationError(str(exc), {"from": old_status, "to": payload.status})
    project.status = payload.status
    audit_service.record(
        db,
        "project",
        project.id,
        "status_changed",
        actor=payload.actor or "system",
        from_status=old_status,
        to_status=payload.status,
        metadata={"note": (payload.note or f"Project status changed to {payload.status}.")},
    )
    db.commit()
    db.refresh(project)
    return project


def _validate_site_items(site_items: list) -> list[dict]:
    if not isinstance(site_items, list) or not site_items:
        raise ValidationError(
            "Template site_items must be a non-empty JSON array.",
            {"site_items": site_items},
        )
    normalized: list[dict] = []
    seen_codes: set[str] = set()
    for idx, item in enumerate(site_items):
        if not isinstance(item, dict):
            raise ValidationError(
                f"site_items[{idx}] must be an object.",
                {"index": idx, "value": item},
            )
        code = str(item.get("site_code") or "").strip()
        name = str(item.get("site_name") or "").strip()
        if not code:
            raise ValidationError(
                f"site_items[{idx}].site_code is required.",
                {"index": idx, "field": "site_code"},
            )
        if not name:
            raise ValidationError(
                f"site_items[{idx}].site_name is required.",
                {"index": idx, "field": "site_name"},
            )
        if code in seen_codes:
            raise ValidationError(
                f"Duplicate site_code '{code}' in template items.",
                {"site_code": code, "index": idx},
            )
        seen_codes.add(code)
        normalized.append(
            {
                "site_code": code,
                "site_name": name,
                "address_text": str(item.get("address_text") or "").strip(),
                "region": str(item.get("region") or "").strip(),
            }
        )
    return normalized


@router.post("/from-template", response_model=ProjectRiskSummary, status_code=201)
def create_project_from_template(
    payload: ProjectFromTemplate,
    db: Session = Depends(get_db),
):
    template = db.get(SiteTemplate, payload.template_id)
    if not template:
        raise NotFoundError("Template not found", {"template_id": payload.template_id})

    normalized_items = _validate_site_items(template.site_items or [])

    existing = db.query(Site).filter(
        Site.site_code.in_([it["site_code"] for it in normalized_items])
    ).first()
    if existing:
        raise ConflictError(
            f"Site code '{existing.site_code}' already exists.",
            {"site_code": existing.site_code},
        )

    try:
        project = Project(
            project_code=payload.project_code,
            project_name=payload.project_name,
            owner_name=payload.owner_name,
            status="draft",
        )
        db.add(project)
        db.flush()

        for item in normalized_items:
            site = Site(
                site_code=item["site_code"],
                site_name=item["site_name"],
                address_text=item["address_text"],
                region=item["region"] or template.default_region or "",
                project_id=project.id,
            )
            db.add(site)

        db.flush()
        site_ids = [s.id for s in project.sites]

        audit_service.record(
            db,
            "project",
            project.id,
            "created_from_template",
            actor=payload.owner_name,
            metadata={
                "template_id": template.id,
                "template_name": template.template_name,
                "site_count": len(normalized_items),
                "note": f"Project created from template with {len(normalized_items)} sites in one transaction.",
            },
        )
        for sid in site_ids:
            audit_service.record(
                db, "site", sid, "created",
                metadata={"project_id": project.id, "note": "Site generated from template."},
            )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            f"Project code '{payload.project_code}' already exists.",
            {"project_code": payload.project_code},
        )
    except ValidationError:
        db.rollback()
        raise

    db.refresh(project)
    return compute_project_risk_summary(db, project)
