from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.all_models import SiteTemplate
from app.schemas.template import SiteTemplate as TemplateSchema, TemplateCreate
from app.services import audit_service

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=TemplateSchema, status_code=201)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)):
    tpl = SiteTemplate(
        template_name=payload.template_name,
        default_region=payload.default_region or "",
        site_items=payload.site_items,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    audit_service.record(db, "template", tpl.id, "created", metadata={"template_name": tpl.template_name})
    db.commit()
    return tpl


@router.get("", response_model=list[TemplateSchema])
def list_templates(db: Session = Depends(get_db)):
    return db.query(SiteTemplate).order_by(SiteTemplate.created_at.desc()).all()


@router.get("/{template_id}", response_model=TemplateSchema)
def get_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.get(SiteTemplate, template_id)
    if not tpl:
        raise NotFoundError("Template not found", {"template_id": template_id})
    return tpl
