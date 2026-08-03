from fastapi import APIRouter, Query
from typing import List, Optional
from ..database import get_db
from ..schemas import AttachmentCreate, Attachment
from ..errors import NotFoundError
from ..audit import record_audit

router = APIRouter()


def row_to_attachment(row):
    return {
        "id": row["id"],
        "file_name": row["file_name"],
        "file_type": row["file_type"],
        "storage_note": row["storage_note"],
        "linked_finding_id": row["linked_finding_id"],
        "created_at": row["created_at"],
    }


@router.post("/attachments", response_model=Attachment)
def create_attachment(payload: AttachmentCreate):
    with get_db() as db:
        if payload.linked_finding_id is not None:
            finding = db.execute("SELECT id FROM findings WHERE id = ?", (payload.linked_finding_id,)).fetchone()
            if not finding:
                raise NotFoundError("finding", payload.linked_finding_id)
        cur = db.execute(
            "INSERT INTO attachments (file_name, file_type, storage_note, linked_finding_id) VALUES (?, ?, ?, ?)",
            (payload.file_name, payload.file_type, payload.storage_note, payload.linked_finding_id),
        )
        aid = cur.lastrowid
        record_audit(db, "attachment", aid, "register", "", {
            "file_name": payload.file_name,
            "linked_finding_id": payload.linked_finding_id,
        })
        row = db.execute("SELECT * FROM attachments WHERE id = ?", (aid,)).fetchone()
    return row_to_attachment(row)


@router.get("/attachments", response_model=List[Attachment])
def list_attachments(
    linked_finding_id: Optional[int] = Query(None),
):
    with get_db() as db:
        if linked_finding_id is not None:
            rows = db.execute(
                "SELECT * FROM attachments WHERE linked_finding_id = ? ORDER BY id",
                (linked_finding_id,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM attachments ORDER BY id").fetchall()
    return [row_to_attachment(r) for r in rows]


@router.get("/attachments/{attachment_id}", response_model=Attachment)
def get_attachment(attachment_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
    if not row:
        raise NotFoundError("attachment", attachment_id)
    return row_to_attachment(row)


@router.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
        if not row:
            raise NotFoundError("attachment", attachment_id)
        db.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        record_audit(db, "attachment", attachment_id, "delete", "", {})
    return {"deleted": attachment_id}
