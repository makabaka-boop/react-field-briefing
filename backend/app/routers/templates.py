from fastapi import APIRouter
from typing import List
import json
from ..database import get_db
from ..schemas import TemplateCreate, Template
from ..errors import NotFoundError, ConflictError, ValidationError
from ..audit import record_audit

router = APIRouter()


def row_to_template(row):
    return {
        "id": row["id"],
        "template_name": row["template_name"],
        "default_region": row["default_region"],
        "site_items": json.loads(row["site_items"]),
    }


@router.post("/templates", response_model=Template)
def create_template(payload: TemplateCreate):
    if not payload.template_name:
        raise ValidationError("template_name is required")
    with get_db() as db:
        existing = db.execute("SELECT id FROM templates WHERE template_name = ?", (payload.template_name,)).fetchone()
        if existing:
            raise ConflictError(f"Template name {payload.template_name} already exists", {"template_name": payload.template_name})
        items = []
        for item in payload.site_items:
            items.append({
                "site_code": item.site_code,
                "site_name": item.site_name,
                "address_text": item.address_text,
                "region": item.region or payload.default_region,
            })
        cur = db.execute(
            "INSERT INTO templates (template_name, default_region, site_items) VALUES (?, ?, ?)",
            (payload.template_name, payload.default_region, json.dumps(items, ensure_ascii=False)),
        )
        tid = cur.lastrowid
        record_audit(db, "template", tid, "create", "", {"template_name": payload.template_name, "item_count": len(items)})
        row = db.execute("SELECT * FROM templates WHERE id = ?", (tid,)).fetchone()
    return row_to_template(row)


@router.get("/templates", response_model=List[Template])
def list_templates():
    with get_db() as db:
        rows = db.execute("SELECT * FROM templates ORDER BY id DESC").fetchall()
    return [row_to_template(r) for r in rows]


@router.get("/templates/{template_id}", response_model=Template)
def get_template(template_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    if not row:
        raise NotFoundError("template", template_id)
    return row_to_template(row)


@router.delete("/templates/{template_id}")
def delete_template(template_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
        if not row:
            raise NotFoundError("template", template_id)
        db.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        record_audit(db, "template", template_id, "delete", "", {})
    return {"deleted": template_id}
