from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError, ValidationError
from app.core.state_machine import StatusMachine
from app.models.all_models import Finding, Review
from app.schemas.review import Review as ReviewSchema, ReviewCreate
from app.services import audit_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewSchema, status_code=201)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    finding = db.get(Finding, payload.finding_id)
    if not finding:
        raise NotFoundError("Finding not found", {"finding_id": payload.finding_id})

    review = Review(
        finding_id=payload.finding_id,
        reviewer_name=payload.reviewer_name,
        conclusion=payload.conclusion,
        comment=payload.comment or "",
    )
    db.add(review)
    db.flush()

    old = finding.finding_status
    target = "accepted" if payload.conclusion == "accepted" else "rejected"
    try:
        StatusMachine.validate(old, target, kind="finding")
    except Exception as exc:
        db.rollback()
        raise ValidationError(str(exc), {"from": old, "to": target})
    finding.finding_status = target

    audit_service.record(
        db, "review", review.id, "review_concluded",
        actor=payload.reviewer_name,
        metadata={
            "finding_id": finding.id,
            "conclusion": payload.conclusion,
            "comment": payload.comment or "",
            "note": f"Review {payload.conclusion}: {payload.comment or 'no comment'}".strip(),
        },
    )
    note = (
        f"Finding {target} after review by {payload.reviewer_name}."
        + (f" Comment: {payload.comment}" if payload.comment else "")
    )
    audit_service.record(
        db, "finding", finding.id, "status_changed",
        actor=payload.reviewer_name,
        from_status=old, to_status=target,
        metadata={"note": note, "review_id": review.id},
    )
    db.commit()
    db.refresh(review)
    return review


@router.get("/by-finding/{finding_id}", response_model=list[ReviewSchema])
def list_reviews(finding_id: int, db: Session = Depends(get_db)):
    return db.query(Review).filter(Review.finding_id == finding_id).order_by(Review.reviewed_at.desc()).all()
