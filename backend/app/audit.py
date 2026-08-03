import json


def record_audit(conn, entity_type: str, entity_id: int, action: str, actor: str = "", details: dict = None):
    conn.execute(
        "INSERT INTO audit_events (entity_type, entity_id, action, actor, details) VALUES (?, ?, ?, ?, ?)",
        (entity_type, entity_id, action, actor, json.dumps(details or {}, ensure_ascii=False)),
    )
