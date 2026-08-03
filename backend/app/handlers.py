"""各接口处理函数。

导入本模块即通过 @route 装饰器向 router.ROUTES 注册全部路由。
"""
import json
import sqlite3

from .db import utc_now
from .errors import ApiError
from .router import route
from .state_machine import STATUSES, transition

RISK_LEVELS = ("low", "medium", "high", "critical")

# 未复核状态集合：尚未得出复核结论的观察项
UNREVIEWED_STATUSES = ("draft", "submitted", "reviewing")

# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------


def project_dict(row, sites=None):
    data = {
        "id": row["id"],
        "project_code": row["project_code"],
        "project_name": row["project_name"],
        "owner_name": row["owner_name"],
        "status": row["status"],
        "created_at": row["created_at"],
    }
    if sites is not None:
        data["sites"] = sites
    return data


def site_dict(row, findings=None):
    data = {
        "id": row["id"],
        "site_code": row["site_code"],
        "site_name": row["site_name"],
        "address_text": row["address_text"],
        "region": row["region"],
        "project_id": row["project_id"],
    }
    if findings is not None:
        data["findings"] = findings
    return data


def finding_dict(row):
    return {
        "id": row["id"],
        "site_id": row["site_id"],
        "category": row["category"],
        "description": row["description"],
        "risk_level": row["risk_level"],
        "finding_status": row["finding_status"],
        "reported_by": row["reported_by"],
        "reported_at": row["reported_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def template_dict(row):
    return {
        "id": row["id"],
        "template_name": row["template_name"],
        "default_region": row["default_region"],
        "site_items": json.loads(row["site_items"]),
        "created_at": row["created_at"],
    }


def review_dict(row):
    return {
        "id": row["id"],
        "finding_id": row["finding_id"],
        "reviewer_name": row["reviewer_name"],
        "conclusion": row["conclusion"],
        "comment": row["comment"],
        "created_at": row["created_at"],
    }


def attachment_dict(row):
    return {
        "id": row["id"],
        "file_name": row["file_name"],
        "file_type": row["file_type"],
        "storage_note": row["storage_note"],
        "linked_finding_id": row["linked_finding_id"],
        "created_at": row["created_at"],
    }


def audit_event_dict(row):
    return {
        "id": row["id"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "action": row["action"],
        "actor": row["actor"],
        "detail": json.loads(row["detail"] or "{}"),
        "project_id": row["project_id"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# 校验与取数辅助
# ---------------------------------------------------------------------------


def _require_body(req):
    if not isinstance(req.body, dict):
        raise ApiError(400, "VALIDATION_ERROR", "request body must be a JSON object")
    return req.body


def _require_fields(body, fields):
    missing = [name for name in fields if body.get(name) is None or body.get(name) == ""]
    if missing:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "missing required field(s): %s" % ", ".join(missing),
            {"missing_fields": missing},
        )


def _require_non_empty_string(body, name):
    """字段必须是非空字符串（纯空白视为空），返回原始值。"""
    value = body.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "field '%s' must be a non-empty string" % name,
            {"field": name},
        )
    return value


def _require_int_field(body, name):
    value = body.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "field '%s' must be an integer" % name,
            {"field": name},
        )
    return value


def _path_int(req, name):
    try:
        return int(req.path_params[name])
    except (KeyError, TypeError, ValueError):
        raise ApiError(404, "NOT_FOUND", "resource not found: %s" % req.path)


def _query_int(req, name):
    raw = req.query.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "query parameter '%s' must be an integer" % name,
            {"field": name},
        )


def _check_risk_level(value):
    if value not in RISK_LEVELS:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "risk_level must be one of: %s" % ", ".join(RISK_LEVELS),
            {"field": "risk_level", "allowed": list(RISK_LEVELS)},
        )


def _reject_unknown_fields(body, allowed):
    unknown = sorted(set(body) - set(allowed))
    if unknown:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "field(s) not allowed: %s" % ", ".join(unknown),
            {"unknown_fields": unknown, "allowed_fields": list(allowed)},
        )


def _get_project_or_404(conn, project_id):
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise ApiError(404, "PROJECT_NOT_FOUND", "project %s not found" % project_id,
                       {"project_id": project_id})
    return row


def _get_site_or_404(conn, site_id):
    row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
    if row is None:
        raise ApiError(404, "SITE_NOT_FOUND", "site %s not found" % site_id,
                       {"site_id": site_id})
    return row


def _get_finding_or_404(conn, finding_id):
    row = conn.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    if row is None:
        raise ApiError(404, "FINDING_NOT_FOUND", "finding %s not found" % finding_id,
                       {"finding_id": finding_id})
    return row


def _project_id_for_site(conn, site_id):
    row = conn.execute("SELECT project_id FROM sites WHERE id = ?", (site_id,)).fetchone()
    return row["project_id"] if row else None


def _audit(conn, entity_type, entity_id, action, actor="", detail=None, project_id=None):
    conn.execute(
        "INSERT INTO audit_events (entity_type, entity_id, action, actor, detail, project_id, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            entity_type,
            entity_id,
            action,
            actor or "",
            json.dumps(detail if detail is not None else {}, ensure_ascii=False),
            project_id,
            utc_now(),
        ),
    )


# ---------------------------------------------------------------------------
# 项目
# ---------------------------------------------------------------------------


@route("POST", "/api/v1/projects")
def create_project(req):
    body = _require_body(req)
    _require_fields(body, ["project_code", "project_name", "owner_name"])
    with req.conn:
        try:
            cur = req.conn.execute(
                "INSERT INTO projects (project_code, project_name, owner_name, status, created_at)"
                " VALUES (?, ?, ?, 'draft', ?)",
                (body["project_code"], body["project_name"], body["owner_name"], utc_now()),
            )
        except sqlite3.IntegrityError:
            raise ApiError(
                409,
                "DUPLICATE_CODE",
                "project_code '%s' already exists" % body["project_code"],
                {"project_code": body["project_code"]},
            )
        project_id = cur.lastrowid
        _audit(req.conn, "project", project_id, "project_created",
               actor=body["owner_name"],
               detail={"project_code": body["project_code"]},
               project_id=project_id)
    return 201, project_dict(_get_project_or_404(req.conn, project_id))


def _empty_risk_summary():
    return {
        "total_findings": 0,
        "unreviewed_count": 0,
        "rejected_count": 0,
        "max_risk_level": None,
        "last_updated_at": None,
    }


def _project_risk_summaries(conn):
    """按项目聚合风险摘要（基于非 archived 观察项）与地点区域集合。"""
    summaries = {}
    risk_levels_seen = {}
    rows = conn.execute(
        "SELECT s.project_id AS project_id, f.risk_level AS risk_level,"
        " f.finding_status AS finding_status, f.updated_at AS updated_at"
        " FROM findings f JOIN sites s ON s.id = f.site_id"
        " WHERE f.finding_status != 'archived'"
    ).fetchall()
    for row in rows:
        summary = summaries.setdefault(row["project_id"], _empty_risk_summary())
        summary["total_findings"] += 1
        if row["finding_status"] in UNREVIEWED_STATUSES:
            summary["unreviewed_count"] += 1
        if row["finding_status"] == "rejected":
            summary["rejected_count"] += 1
        if row["updated_at"] and (summary["last_updated_at"] is None
                                  or row["updated_at"] > summary["last_updated_at"]):
            summary["last_updated_at"] = row["updated_at"]
        if row["risk_level"] in RISK_LEVELS:
            risk_levels_seen.setdefault(row["project_id"], set()).add(row["risk_level"])
    for project_id, summary in summaries.items():
        seen = risk_levels_seen.get(project_id, set())
        for level in reversed(RISK_LEVELS):
            if level in seen:
                summary["max_risk_level"] = level
                break
    regions = {}
    for row in conn.execute("SELECT project_id, region FROM sites").fetchall():
        if row["region"]:
            regions.setdefault(row["project_id"], set()).add(row["region"])
    return summaries, regions


@route("GET", "/api/v1/projects")
def list_projects(req):
    sql = "SELECT * FROM projects"
    args = []
    if "status" in req.query:
        sql += " WHERE status = ?"
        args.append(req.query["status"])
    sql += " ORDER BY id"
    rows = req.conn.execute(sql, args).fetchall()
    summaries, regions = _project_risk_summaries(req.conn)
    region_filter = req.query.get("region")
    max_risk_filter = req.query.get("max_risk_level")
    if max_risk_filter is not None and max_risk_filter not in RISK_LEVELS:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "max_risk_level must be one of: %s" % ", ".join(RISK_LEVELS),
            {"field": "max_risk_level", "allowed": list(RISK_LEVELS)},
        )
    result = []
    for row in rows:
        summary = summaries.get(row["id"], _empty_risk_summary())
        if region_filter is not None and region_filter not in regions.get(row["id"], set()):
            continue
        if max_risk_filter is not None and summary["max_risk_level"] != max_risk_filter:
            continue
        data = project_dict(row)
        data["risk_summary"] = summary
        data["regions"] = sorted(regions.get(row["id"], set()))
        result.append(data)
    return result


@route("GET", "/api/v1/projects/{project_id}")
def get_project(req):
    project_id = _path_int(req, "project_id")
    project = _get_project_or_404(req.conn, project_id)
    sites = req.conn.execute(
        "SELECT * FROM sites WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    return project_dict(project, sites=[site_dict(row) for row in sites])


@route("POST", "/api/v1/projects/from_template")
def create_project_from_template(req):
    body = _require_body(req)
    _require_fields(body, ["project_code", "project_name", "owner_name", "template_id"])
    template_id = _require_int_field(body, "template_id")
    template = req.conn.execute(
        "SELECT * FROM site_templates WHERE id = ?", (template_id,)
    ).fetchone()
    if template is None:
        raise ApiError(404, "TEMPLATE_NOT_FOUND", "template %s not found" % template_id,
                       {"template_id": template_id})
    # 模板 site_items 结构校验（非法则整体拒绝，不写入任何数据）
    try:
        items = json.loads(template["site_items"])
    except (TypeError, ValueError):
        raise ApiError(400, "VALIDATION_ERROR",
                       "template %s has invalid site_items JSON" % template_id,
                       {"template_id": template_id})
    if not isinstance(items, list) or not items:
        raise ApiError(400, "VALIDATION_ERROR",
                       "template %s site_items must be a non-empty array" % template_id,
                       {"template_id": template_id})
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("site_name"), str) \
                or not item["site_name"].strip():
            raise ApiError(
                400,
                "VALIDATION_ERROR",
                "template site_items[%d] must be an object containing site_name" % index,
                {"template_id": template_id, "index": index},
            )
    # 生成地点编码并检查批内重复（重复则整批回滚）
    site_codes = [
        (item.get("site_code") or "SITE-%03d" % (index + 1))
        for index, item in enumerate(items)
    ]
    seen, duplicates = set(), set()
    for code in site_codes:
        if code in seen:
            duplicates.add(code)
        seen.add(code)
    if duplicates:
        raise ApiError(
            409,
            "DUPLICATE_CODE",
            "duplicate site_code(s) in template site_items: %s" % ", ".join(sorted(duplicates)),
            {"template_id": template_id, "duplicate_site_codes": sorted(duplicates)},
        )
    # 单事务：创建项目 + 批量地点；任何一步失败整体回滚
    with req.conn:
        try:
            cur = req.conn.execute(
                "INSERT INTO projects (project_code, project_name, owner_name, status, created_at)"
                " VALUES (?, ?, ?, 'draft', ?)",
                (body["project_code"], body["project_name"], body["owner_name"], utc_now()),
            )
        except sqlite3.IntegrityError:
            raise ApiError(
                409,
                "DUPLICATE_CODE",
                "project_code '%s' already exists" % body["project_code"],
                {"project_code": body["project_code"]},
            )
        project_id = cur.lastrowid
        _audit(req.conn, "project", project_id, "project_created_from_template",
               actor=body["owner_name"],
               detail={"template_id": template_id, "template_name": template["template_name"]},
               project_id=project_id)
        for item, site_code in zip(items, site_codes):
            try:
                cur = req.conn.execute(
                    "INSERT INTO sites (site_code, site_name, address_text, region, project_id)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (site_code, item["site_name"].strip(), item.get("address_text") or "",
                     template["default_region"], project_id),
                )
            except sqlite3.IntegrityError:
                raise ApiError(
                    409,
                    "DUPLICATE_CODE",
                    "site_code '%s' already exists in project %s" % (site_code, project_id),
                    {"site_code": site_code, "project_id": project_id},
                )
            _audit(req.conn, "site", cur.lastrowid, "site_created",
                   actor=body["owner_name"],
                   detail={"site_code": site_code, "from_template": True},
                   project_id=project_id)
    project = _get_project_or_404(req.conn, project_id)
    sites = req.conn.execute(
        "SELECT * FROM sites WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    return 201, project_dict(project, sites=[site_dict(row) for row in sites])


# ---------------------------------------------------------------------------
# 地点模板
# ---------------------------------------------------------------------------


@route("POST", "/api/v1/site_templates")
def create_site_template(req):
    body = _require_body(req)
    _require_fields(body, ["template_name"])
    site_items = body.get("site_items")
    if not isinstance(site_items, list) or not site_items:
        raise ApiError(400, "VALIDATION_ERROR", "site_items must be a non-empty array",
                       {"field": "site_items"})
    for index, item in enumerate(site_items):
        if not isinstance(item, dict) or not item.get("site_name"):
            raise ApiError(
                400,
                "VALIDATION_ERROR",
                "site_items[%d] must be an object containing site_name" % index,
                {"field": "site_items", "index": index},
            )
    with req.conn:
        try:
            cur = req.conn.execute(
                "INSERT INTO site_templates (template_name, default_region, site_items, created_at)"
                " VALUES (?, ?, ?, ?)",
                (body["template_name"], body.get("default_region") or "",
                 json.dumps(site_items, ensure_ascii=False), utc_now()),
            )
        except sqlite3.IntegrityError:
            raise ApiError(
                409,
                "DUPLICATE_TEMPLATE_NAME",
                "template_name '%s' already exists" % body["template_name"],
                {"template_name": body["template_name"]},
            )
        template_id = cur.lastrowid
        _audit(req.conn, "site_template", template_id, "template_created",
               detail={"template_name": body["template_name"]})
    row = req.conn.execute(
        "SELECT * FROM site_templates WHERE id = ?", (template_id,)
    ).fetchone()
    return 201, template_dict(row)


@route("GET", "/api/v1/site_templates")
def list_site_templates(req):
    rows = req.conn.execute("SELECT * FROM site_templates ORDER BY id").fetchall()
    return [template_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# 地点
# ---------------------------------------------------------------------------


@route("POST", "/api/v1/sites")
def create_site(req):
    body = _require_body(req)
    _require_fields(body, ["site_code", "site_name", "project_id"])
    project_id = _require_int_field(body, "project_id")
    project = _get_project_or_404(req.conn, project_id)
    with req.conn:
        try:
            cur = req.conn.execute(
                "INSERT INTO sites (site_code, site_name, address_text, region, project_id)"
                " VALUES (?, ?, ?, ?, ?)",
                (body["site_code"], body["site_name"], body.get("address_text") or "",
                 body.get("region") or "", project_id),
            )
        except sqlite3.IntegrityError:
            raise ApiError(
                409,
                "DUPLICATE_CODE",
                "site_code '%s' already exists in project %s" % (body["site_code"], project_id),
                {"site_code": body["site_code"], "project_id": project_id},
            )
        site_id = cur.lastrowid
        _audit(req.conn, "site", site_id, "site_created",
               actor=project["owner_name"],
               detail={"site_code": body["site_code"]},
               project_id=project_id)
    return 201, site_dict(_get_site_or_404(req.conn, site_id))


@route("GET", "/api/v1/sites")
def list_sites(req):
    clauses, args = [], []
    project_id = _query_int(req, "project_id")
    if project_id is not None:
        clauses.append("project_id = ?")
        args.append(project_id)
    if "region" in req.query:
        clauses.append("region = ?")
        args.append(req.query["region"])
    sql = "SELECT * FROM sites"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"
    rows = req.conn.execute(sql, args).fetchall()
    return [site_dict(row) for row in rows]


@route("GET", "/api/v1/sites/{site_id}")
def get_site(req):
    site_id = _path_int(req, "site_id")
    site = _get_site_or_404(req.conn, site_id)
    findings = req.conn.execute(
        "SELECT * FROM findings WHERE site_id = ? ORDER BY id", (site_id,)
    ).fetchall()
    return site_dict(site, findings=[finding_dict(row) for row in findings])


@route("PATCH", "/api/v1/sites/{site_id}")
def update_site(req):
    site_id = _path_int(req, "site_id")
    body = _require_body(req)
    _get_site_or_404(req.conn, site_id)
    allowed = ("site_name", "address_text", "region")
    _reject_unknown_fields(body, allowed)
    updates = {key: body[key] for key in allowed if key in body}
    if not updates:
        raise ApiError(400, "VALIDATION_ERROR",
                       "no fields to update; allowed: %s" % ", ".join(allowed),
                       {"allowed_fields": list(allowed)})
    assignments = ", ".join("%s = ?" % key for key in updates)
    with req.conn:
        req.conn.execute(
            "UPDATE sites SET %s WHERE id = ?" % assignments,
            list(updates.values()) + [site_id],
        )
    return site_dict(_get_site_or_404(req.conn, site_id))


# ---------------------------------------------------------------------------
# 观察项
# ---------------------------------------------------------------------------


@route("POST", "/api/v1/findings")
def create_finding(req):
    body = _require_body(req)
    _require_fields(body, ["site_id", "category", "description", "risk_level", "reported_by"])
    site_id = _require_int_field(body, "site_id")
    category = _require_non_empty_string(body, "category").strip()
    description = _require_non_empty_string(body, "description").strip()
    risk_level = _require_non_empty_string(body, "risk_level").strip()
    reported_by = _require_non_empty_string(body, "reported_by").strip()
    _check_risk_level(risk_level)
    site = _get_site_or_404(req.conn, site_id)
    now = utc_now()
    with req.conn:
        cur = req.conn.execute(
            "INSERT INTO findings (site_id, category, description, risk_level, finding_status,"
            " reported_by, reported_at, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, 'draft', ?, NULL, ?, ?)",
            (site_id, category, description, risk_level, reported_by, now, now),
        )
        finding_id = cur.lastrowid
        _audit(req.conn, "finding", finding_id, "finding_created",
               actor=reported_by,
               detail={"site_id": site_id, "category": category,
                       "risk_level": risk_level},
               project_id=site["project_id"])
    return 201, finding_dict(_get_finding_or_404(req.conn, finding_id))


@route("PATCH", "/api/v1/findings/{finding_id}")
def update_finding(req):
    finding_id = _path_int(req, "finding_id")
    body = _require_body(req)
    finding = _get_finding_or_404(req.conn, finding_id)
    if finding["finding_status"] != "draft":
        raise ApiError(
            409,
            "INVALID_STATE_TRANSITION",
            "only draft findings can be edited (current status: %s)" % finding["finding_status"],
            {"current_status": finding["finding_status"]},
        )
    allowed = ("category", "description", "risk_level")
    _reject_unknown_fields(body, allowed)
    updates = {key: body[key] for key in allowed if key in body}
    if not updates:
        raise ApiError(400, "VALIDATION_ERROR",
                       "no fields to update; allowed: %s" % ", ".join(allowed),
                       {"allowed_fields": list(allowed)})
    for key in updates:
        updates[key] = _require_non_empty_string(updates, key).strip()
    if "risk_level" in updates:
        _check_risk_level(updates["risk_level"])
    updates["updated_at"] = utc_now()
    assignments = ", ".join("%s = ?" % key for key in updates)
    with req.conn:
        req.conn.execute(
            "UPDATE findings SET %s WHERE id = ?" % assignments,
            list(updates.values()) + [finding_id],
        )
    return finding_dict(_get_finding_or_404(req.conn, finding_id))


@route("POST", "/api/v1/findings/{finding_id}/submit")
def submit_finding(req):
    finding_id = _path_int(req, "finding_id")
    finding = _get_finding_or_404(req.conn, finding_id)
    transition(finding["finding_status"], "submitted")
    now = utc_now()
    with req.conn:
        req.conn.execute(
            "UPDATE findings SET finding_status = 'submitted', reported_at = ?, updated_at = ?"
            " WHERE id = ?",
            (now, now, finding_id),
        )
        _audit(req.conn, "finding", finding_id, "finding_submitted",
               actor=finding["reported_by"],
               detail={"site_id": finding["site_id"]},
               project_id=_project_id_for_site(req.conn, finding["site_id"]))
    return finding_dict(_get_finding_or_404(req.conn, finding_id))


@route("POST", "/api/v1/findings/{finding_id}/transition")
def transition_finding(req):
    finding_id = _path_int(req, "finding_id")
    body = _require_body(req)
    _require_fields(body, ["to_status"])
    to_status = body["to_status"]
    if to_status not in STATUSES:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "to_status must be one of: %s" % ", ".join(STATUSES),
            {"field": "to_status", "allowed": list(STATUSES)},
        )
    finding = _get_finding_or_404(req.conn, finding_id)
    from_status = finding["finding_status"]
    transition(from_status, to_status)
    actor = body.get("actor") or finding["reported_by"]
    note = body.get("note") or ""
    with req.conn:
        req.conn.execute(
            "UPDATE findings SET finding_status = ?, updated_at = ? WHERE id = ?",
            (to_status, utc_now(), finding_id),
        )
        _audit(req.conn, "finding", finding_id, "status_transition",
               actor=actor,
               detail={"from_status": from_status, "to_status": to_status,
                       "note": note},
               project_id=_project_id_for_site(req.conn, finding["site_id"]))
    return finding_dict(_get_finding_or_404(req.conn, finding_id))


@route("POST", "/api/v1/findings/{finding_id}/review")
def review_finding(req):
    finding_id = _path_int(req, "finding_id")
    body = _require_body(req)
    _require_fields(body, ["reviewer_name", "conclusion"])
    conclusion = body["conclusion"]
    if conclusion not in ("accepted", "rejected"):
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "conclusion must be 'accepted' or 'rejected'",
            {"field": "conclusion", "allowed": ["accepted", "rejected"]},
        )
    finding = _get_finding_or_404(req.conn, finding_id)
    if finding["finding_status"] != "reviewing":
        raise ApiError(
            409,
            "INVALID_STATE_TRANSITION",
            "finding must be in reviewing status to be reviewed (current status: %s)"
            % finding["finding_status"],
            {"current_status": finding["finding_status"], "required_status": "reviewing"},
        )
    transition(finding["finding_status"], conclusion)
    now = utc_now()
    with req.conn:
        cur = req.conn.execute(
            "INSERT INTO reviews (finding_id, reviewer_name, conclusion, comment, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (finding_id, body["reviewer_name"], conclusion, body.get("comment") or "", now),
        )
        review_id = cur.lastrowid
        req.conn.execute(
            "UPDATE findings SET finding_status = ?, updated_at = ? WHERE id = ?",
            (conclusion, now, finding_id),
        )
        _audit(req.conn, "finding", finding_id, "finding_reviewed",
               actor=body["reviewer_name"],
               detail={"conclusion": conclusion, "reviewer": body["reviewer_name"],
                       "review_id": review_id,
                       "from_status": "reviewing", "to_status": conclusion,
                       "note": body.get("comment") or ""},
               project_id=_project_id_for_site(req.conn, finding["site_id"]))
    row = req.conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    return 201, review_dict(row)


@route("GET", "/api/v1/findings/{finding_id}/reviews")
def list_finding_reviews(req):
    finding_id = _path_int(req, "finding_id")
    _get_finding_or_404(req.conn, finding_id)
    rows = req.conn.execute(
        "SELECT * FROM reviews WHERE finding_id = ? ORDER BY id", (finding_id,)
    ).fetchall()
    return [review_dict(row) for row in rows]


@route("GET", "/api/v1/findings/{finding_id}/timeline")
def finding_timeline(req):
    """观察项时间线：观察项本身、附件元数据与审计事件按时间合并排列。

    返回项的 item_type 取值：finding / attachment / audit_event。
    """
    finding_id = _path_int(req, "finding_id")
    finding = _get_finding_or_404(req.conn, finding_id)
    items = [{
        "item_type": "finding",
        "created_at": finding["created_at"],
        "finding": finding_dict(finding),
    }]
    event_rows = req.conn.execute(
        "SELECT id, action, actor, detail, created_at FROM audit_events"
        " WHERE entity_type = 'finding' AND entity_id = ?"
        " ORDER BY created_at ASC, id ASC",
        (finding_id,),
    ).fetchall()
    for row in event_rows:
        items.append({
            "item_type": "audit_event",
            "created_at": row["created_at"],
            "action": row["action"],
            "actor": row["actor"],
            "detail": json.loads(row["detail"] or "{}"),
            "_seq": row["id"],
        })
    attachment_rows = req.conn.execute(
        "SELECT * FROM attachments WHERE linked_finding_id = ? ORDER BY id",
        (finding_id,),
    ).fetchall()
    for row in attachment_rows:
        items.append({
            "item_type": "attachment",
            "created_at": row["created_at"],
            "attachment": attachment_dict(row),
            "_seq": row["id"],
        })
    type_rank = {"finding": 0, "audit_event": 1, "attachment": 2}
    items.sort(key=lambda item: (item["created_at"],
                                 type_rank[item["item_type"]],
                                 item.get("_seq", 0)))
    for item in items:
        item.pop("_seq", None)
    return items


@route("GET", "/api/v1/findings")
def list_findings(req):
    clauses, args = [], []
    site_id = _query_int(req, "site_id")
    if site_id is not None:
        clauses.append("f.site_id = ?")
        args.append(site_id)
    project_id = _query_int(req, "project_id")
    if project_id is not None:
        clauses.append("s.project_id = ?")
        args.append(project_id)
    for param, column in (("finding_status", "f.finding_status"),
                          ("risk_level", "f.risk_level"),
                          ("category", "f.category")):
        if param in req.query:
            clauses.append("%s = ?" % column)
            args.append(req.query[param])
    sql = ("SELECT f.*, s.site_name AS site_name, s.site_code AS site_code,"
           " s.project_id AS project_id"
           " FROM findings f JOIN sites s ON s.id = f.site_id")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY f.id"
    rows = req.conn.execute(sql, args).fetchall()
    result = []
    for row in rows:
        data = finding_dict(row)
        data["site_name"] = row["site_name"]
        data["site_code"] = row["site_code"]
        data["project_id"] = row["project_id"]
        result.append(data)
    return result


# ---------------------------------------------------------------------------
# 附件
# ---------------------------------------------------------------------------


@route("POST", "/api/v1/attachments")
def create_attachment(req):
    body = _require_body(req)
    _require_fields(body, ["file_name", "file_type", "linked_finding_id"])
    finding_id = _require_int_field(body, "linked_finding_id")
    finding = _get_finding_or_404(req.conn, finding_id)
    with req.conn:
        cur = req.conn.execute(
            "INSERT INTO attachments (file_name, file_type, storage_note, linked_finding_id, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (body["file_name"], body["file_type"], body.get("storage_note") or "",
             finding_id, utc_now()),
        )
        attachment_id = cur.lastrowid
        _audit(req.conn, "attachment", attachment_id, "attachment_registered",
               actor=finding["reported_by"],
               detail={"file_name": body["file_name"], "linked_finding_id": finding_id},
               project_id=_project_id_for_site(req.conn, finding["site_id"]))
    row = req.conn.execute(
        "SELECT * FROM attachments WHERE id = ?", (attachment_id,)
    ).fetchone()
    return 201, attachment_dict(row)


@route("GET", "/api/v1/attachments")
def list_attachments(req):
    clauses, args = [], []
    linked_finding_id = _query_int(req, "linked_finding_id")
    if linked_finding_id is not None:
        clauses.append("linked_finding_id = ?")
        args.append(linked_finding_id)
    sql = "SELECT * FROM attachments"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"
    rows = req.conn.execute(sql, args).fetchall()
    return [attachment_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# 一致性自检
# ---------------------------------------------------------------------------


def _check_result(check_code, check_name, issues):
    return {
        "check_code": check_code,
        "check_name": check_name,
        "passed": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
    }


# 审计动作隐含的观察项状态（用于状态一致性比对）
_ACTION_IMPLIED_STATUS = {
    "finding_created": "draft",
    "finding_submitted": "submitted",
}


@route("GET", "/api/v1/consistency_checks")
def consistency_checks(req):
    """一致性自检：交付前确认字段、状态、模板与历史数据没有漂移。"""
    conn = req.conn
    checks = []

    # 1. 地点是否指向不存在的项目
    rows = conn.execute(
        "SELECT s.id AS site_id, s.site_code AS site_code, s.project_id AS project_id"
        " FROM sites s LEFT JOIN projects p ON p.id = s.project_id"
        " WHERE p.id IS NULL ORDER BY s.id"
    ).fetchall()
    checks.append(_check_result(
        "orphan_sites",
        "地点指向不存在的项目",
        [{"site_id": r["site_id"], "site_code": r["site_code"],
          "project_id": r["project_id"]} for r in rows],
    ))

    # 2. 观察项是否缺少地点
    rows = conn.execute(
        "SELECT f.id AS finding_id, f.site_id AS site_id"
        " FROM findings f LEFT JOIN sites s ON s.id = f.site_id"
        " WHERE s.id IS NULL ORDER BY f.id"
    ).fetchall()
    checks.append(_check_result(
        "findings_without_site",
        "观察项缺少地点",
        [{"finding_id": r["finding_id"], "site_id": r["site_id"]} for r in rows],
    ))

    # 3. 观察项状态与最后一条审计事件是否不一致
    rows = conn.execute(
        "SELECT f.id AS finding_id, f.finding_status AS finding_status,"
        " e.id AS event_id, e.action AS action, e.detail AS detail"
        " FROM findings f"
        " JOIN audit_events e ON e.id = ("
        "   SELECT MAX(id) FROM audit_events"
        "   WHERE entity_type = 'finding' AND entity_id = f.id)"
        " ORDER BY f.id"
    ).fetchall()
    issues = []
    for row in rows:
        expected = _ACTION_IMPLIED_STATUS.get(row["action"])
        if expected is None and row["action"] in ("status_transition", "finding_reviewed"):
            detail = json.loads(row["detail"] or "{}")
            expected = detail.get("to_status") or detail.get("conclusion")
        if expected and expected != row["finding_status"]:
            issues.append({
                "finding_id": row["finding_id"],
                "finding_status": row["finding_status"],
                "last_action": row["action"],
                "expected_status": expected,
                "audit_event_id": row["event_id"],
            })
    checks.append(_check_result("status_audit_mismatch", "状态与最后一条审计事件不一致", issues))

    # 4. 附件是否指向不存在的观察项
    rows = conn.execute(
        "SELECT a.id AS attachment_id, a.file_name AS file_name,"
        " a.linked_finding_id AS linked_finding_id"
        " FROM attachments a LEFT JOIN findings f ON f.id = a.linked_finding_id"
        " WHERE f.id IS NULL ORDER BY a.id"
    ).fetchall()
    checks.append(_check_result(
        "orphan_attachments",
        "附件指向不存在的观察项",
        [{"attachment_id": r["attachment_id"], "file_name": r["file_name"],
          "linked_finding_id": r["linked_finding_id"]} for r in rows],
    ))

    # 5. 项目内地点编码重复（模板批量生成场景）
    rows = conn.execute(
        "SELECT project_id, site_code, COUNT(*) AS cnt, GROUP_CONCAT(id) AS site_ids"
        " FROM sites GROUP BY project_id, site_code HAVING COUNT(*) > 1"
        " ORDER BY project_id, site_code"
    ).fetchall()
    checks.append(_check_result(
        "duplicate_site_codes",
        "项目内地点编码重复",
        [{"project_id": r["project_id"], "site_code": r["site_code"],
          "site_count": r["cnt"],
          "site_ids": [int(v) for v in r["site_ids"].split(",")]} for r in rows],
    ))

    # 6. 风险概览统计与明细数量是否不一致
    detail_rows = conn.execute(
        "SELECT s.project_id AS project_id, f.risk_level AS risk_level"
        " FROM findings f JOIN sites s ON s.id = f.site_id"
        " WHERE f.finding_status != 'archived'"
    ).fetchall()
    per_project = {}
    for row in detail_rows:
        stat = per_project.setdefault(row["project_id"], {"total": 0, "levels": {}})
        stat["total"] += 1
        stat["levels"][row["risk_level"]] = stat["levels"].get(row["risk_level"], 0) + 1
    issues = []
    for project_id in sorted(per_project):
        stat = per_project[project_id]
        counted_total = sum(stat["levels"].get(level, 0) for level in RISK_LEVELS)
        invalid_levels = sorted(set(stat["levels"]) - set(RISK_LEVELS))
        if counted_total != stat["total"] or invalid_levels:
            issues.append({
                "project_id": project_id,
                "detail_total": stat["total"],
                "counted_total": counted_total,
                "invalid_risk_levels": invalid_levels,
            })
    checks.append(_check_result(
        "risk_summary_mismatch", "风险概览统计与明细数量不一致", issues))

    return {
        "passed": all(check["passed"] for check in checks),
        "total_issues": sum(check["issue_count"] for check in checks),
        "checks": checks,
    }


@route("GET", "/api/v1/audit_events")
def list_audit_events(req):
    clauses, args = [], []
    if "entity_type" in req.query:
        clauses.append("entity_type = ?")
        args.append(req.query["entity_type"])
    entity_id = _query_int(req, "entity_id")
    if entity_id is not None:
        clauses.append("entity_id = ?")
        args.append(entity_id)
    project_id = _query_int(req, "project_id")
    if project_id is not None:
        clauses.append("project_id = ?")
        args.append(project_id)
    sql = "SELECT * FROM audit_events"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"
    rows = req.conn.execute(sql, args).fetchall()
    return [audit_event_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# 风险视图
# ---------------------------------------------------------------------------


@route("GET", "/api/v1/projects/{project_id}/risk_sites")
def project_risk_sites(req):
    """按项目返回各地点风险统计（排除 archived 观察项）。

    每个地点包含：观察项数量、未复核数量、已驳回数量、最高风险等级、最近更新时间。
    """
    project_id = _path_int(req, "project_id")
    _get_project_or_404(req.conn, project_id)
    sites = req.conn.execute(
        "SELECT * FROM sites WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    finding_rows = req.conn.execute(
        "SELECT f.site_id AS site_id, f.risk_level AS risk_level,"
        " f.finding_status AS finding_status, f.updated_at AS updated_at"
        " FROM findings f JOIN sites s ON s.id = f.site_id"
        " WHERE s.project_id = ? AND f.finding_status != 'archived'",
        (project_id,),
    ).fetchall()
    per_site = {}
    for row in finding_rows:
        stat = per_site.setdefault(row["site_id"], {
            "risk_counts": {level: 0 for level in RISK_LEVELS},
            "unreviewed_count": 0,
            "rejected_count": 0,
            "last_updated_at": None,
        })
        if row["risk_level"] in stat["risk_counts"]:
            stat["risk_counts"][row["risk_level"]] += 1
        if row["finding_status"] in UNREVIEWED_STATUSES:
            stat["unreviewed_count"] += 1
        if row["finding_status"] == "rejected":
            stat["rejected_count"] += 1
        if row["updated_at"] and (stat["last_updated_at"] is None
                                  or row["updated_at"] > stat["last_updated_at"]):
            stat["last_updated_at"] = row["updated_at"]
    result = []
    for site in sites:
        stat = per_site.get(site["id"], {
            "risk_counts": {level: 0 for level in RISK_LEVELS},
            "unreviewed_count": 0,
            "rejected_count": 0,
            "last_updated_at": None,
        })
        risk_counts = stat["risk_counts"]
        max_risk_level = None
        for level in reversed(RISK_LEVELS):
            if risk_counts[level] > 0:
                max_risk_level = level
                break
        result.append({
            "site_id": site["id"],
            "site_code": site["site_code"],
            "site_name": site["site_name"],
            "region": site["region"],
            "finding_count": sum(risk_counts.values()),
            "unreviewed_count": stat["unreviewed_count"],
            "rejected_count": stat["rejected_count"],
            "max_risk_level": max_risk_level,
            "last_updated_at": stat["last_updated_at"],
            "risk_counts": risk_counts,
        })
    return result


@route("GET", "/api/v1/projects/{project_id}/risk_summary")
def project_risk_summary(req):
    """项目风险概览（统计排除 archived 观察项，archived 数以 archived_count 单独返回）。"""
    project_id = _path_int(req, "project_id")
    _get_project_or_404(req.conn, project_id)
    total_sites = req.conn.execute(
        "SELECT COUNT(*) AS cnt FROM sites WHERE project_id = ?", (project_id,)
    ).fetchone()["cnt"]
    by_risk_level = {level: 0 for level in RISK_LEVELS}
    by_status = {status: 0 for status in STATUSES}
    rows = req.conn.execute(
        "SELECT f.risk_level AS risk_level, f.finding_status AS finding_status,"
        " f.updated_at AS updated_at"
        " FROM findings f JOIN sites s ON s.id = f.site_id"
        " WHERE s.project_id = ?",
        (project_id,),
    ).fetchall()
    total_findings = 0
    unreviewed_count = 0
    rejected_count = 0
    archived_count = 0
    last_updated_at = None
    for row in rows:
        if row["finding_status"] == "archived":
            archived_count += 1
            continue
        if row["risk_level"] in by_risk_level:
            by_risk_level[row["risk_level"]] += 1
        if row["finding_status"] in by_status:
            by_status[row["finding_status"]] += 1
        if row["finding_status"] in UNREVIEWED_STATUSES:
            unreviewed_count += 1
        if row["finding_status"] == "rejected":
            rejected_count += 1
        if row["updated_at"] and (last_updated_at is None
                                  or row["updated_at"] > last_updated_at):
            last_updated_at = row["updated_at"]
        total_findings += 1
    return {
        "project_id": project_id,
        "total_sites": total_sites,
        "total_findings": total_findings,
        "unreviewed_count": unreviewed_count,
        "rejected_count": rejected_count,
        "archived_count": archived_count,
        "last_updated_at": last_updated_at,
        "by_risk_level": by_risk_level,
        "by_status": by_status,
    }
