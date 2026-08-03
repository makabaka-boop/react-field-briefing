from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.all_models import Attachment, Finding
from app.schemas.attachment import Attachment as AttachmentSchema, AttachmentCreate
from app.services import audit_service

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post("", response_model=AttachmentSchema, status_code=201)
def register_attachment(payload: AttachmentCreate, db: Session = Depends(get_db)):
    finding = db.get(Finding, payload.linked_finding_id)
    if not finding:
        raise NotFoundError(
            "Finding not found",
            {"linked_finding_id": payload.linked_finding_id},
        )
    att = Attachment(
        file_name=payload.file_name,
        file_type=payload.file_type,
        storage_note=payload.storage_note,
        linked_finding_id=payload.linked_finding_id,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    audit_service.record(
        db, "attachment", att.id, "registered",
        metadata={"linked_finding_id": att.linked_finding_id, "file_name": att.file_name},
    )
    db.commit()
    return att


@router.get("/by-finding/{finding_id}", response_model=list[AttachmentSchema])
def list_attachments(finding_id: int, db: Session = Depends(get_db)):
    return db.query(Attachment).filter(Attachment.linked_finding_id == finding_id).all()
