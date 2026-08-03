from fastapi import APIRouter
from typing import List
from ..database import get_db
from ..schemas import ReviewCreate, Review
from ..errors import NotFoundError, ValidationError
from ..state_machine import transition_finding
from ..audit import record_audit

router = APIRouter()


def row_to_review(row):
    return {
        "id": row["id"],
        "finding_id": row["finding_id"],
        "reviewer_name": row["reviewer_name"],
        "conclusion": row["conclusion"],
        "comment": row["comment"],
        "reviewed_at": row["reviewed_at"],
    }


@router.post("/findings/{finding_id}/reviews", response_model=Review)
def create_review(finding_id: int, payload: ReviewCreate):
    valid_conclusions = {"approved", "rejected", "needs_changes"}
    if payload.conclusion not in valid_conclusions:
        raise ValidationError(
            f"Invalid conclusion: {payload.conclusion}",
            {"allowed": sorted(valid_conclusions)},
        )
    with get_db() as db:
        finding = db.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
        if not finding:
            raise NotFoundError("finding", finding_id)
        cur = db.execute(
            "INSERT INTO reviews (finding_id, reviewer_name, conclusion, comment) VALUES (?, ?, ?, ?)",
            (finding_id, payload.reviewer_name, payload.conclusion, payload.comment),
        )
        rid = cur.lastrowid
        old_status = finding["finding_status"]
        new_status = None
        note = ""
        if payload.new_status:
            new_status = transition_finding(old_status, payload.new_status)
            db.execute("UPDATE findings SET finding_status = ? WHERE id = ?", (new_status, finding_id))
            note = f"复核结论：{payload.conclusion}，状态 {old_status} → {new_status}"
        elif payload.conclusion == "approved":
            try:
                new_status = transition_finding(old_status, "accepted")
                db.execute("UPDATE findings SET finding_status = ? WHERE id = ?", (new_status, finding_id))
                note = f"复核通过，状态 {old_status} → {new_status}"
            except Exception:
                note = f"复核结论：{payload.conclusion}（状态未变更）"
        elif payload.conclusion == "rejected":
            try:
                new_status = transition_finding(old_status, "rejected")
                db.execute("UPDATE findings SET finding_status = ? WHERE id = ?", (new_status, finding_id))
                note = f"复核驳回，状态 {old_status} → {new_status}"
            except Exception:
                note = f"复核结论：{payload.conclusion}（状态未变更）"
        else:
            note = f"复核结论：{payload.conclusion}"
        record_audit(db, "finding", finding_id, "review", payload.reviewer_name, {
            "conclusion": payload.conclusion,
            "comment": payload.comment,
            "from_status": old_status,
            "to_status": new_status,
            "actor": payload.reviewer_name,
            "note": note,
        })
        row = db.execute("SELECT * FROM reviews WHERE id = ?", (rid,)).fetchone()
    return row_to_review(row)


@router.get("/findings/{finding_id}/reviews", response_model=List[Review])
def list_reviews(finding_id: int):
    with get_db() as db:
        finding = db.execute("SELECT id FROM findings WHERE id = ?", (finding_id,)).fetchone()
        if not finding:
            raise NotFoundError("finding", finding_id)
        rows = db.execute(
            "SELECT * FROM reviews WHERE finding_id = ? ORDER BY reviewed_at DESC",
            (finding_id,),
        ).fetchall()
    return [row_to_review(r) for r in rows]
