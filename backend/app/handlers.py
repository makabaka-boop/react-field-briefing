"""Request handlers holding all business logic.

Each public method receives already-parsed inputs (path params dict,
query params dict, JSON body) and returns a (status_code, body) tuple.
Handlers never touch the HTTP layer directly, which keeps them unit
testable against an in-memory Database.
"""

import json
import sqlite3
from datetime import datetime, timezone

from . import state_machine as sm
from .errors import ConflictError, NotFoundError, ValidationError
from .validators import clean_str, require_fields


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Handlers:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------ util
    def _record_audit(self, conn, entity_type, entity_id, action,
                      actor_name=None, old_status=None, new_status=None,
                      note=None):
        conn.execute(
            """INSERT INTO audit_events
               (entity_type, entity_id, action, actor_name, old_status,
                new_status, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_type, entity_id, action, actor_name, old_status,
             new_status, note, _now()),
        )

    def _get_project_or_404(self, project_id):
        row = self.db.query_one(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        if row is None:
            raise NotFoundError(
                "Project not found.", details={"project_id": project_id}
            )
        return row

    def _get_site_or_404(self, site_id):
        row = self.db.query_one("SELECT * FROM sites WHERE id = ?", (site_id,))
        if row is None:
            raise NotFoundError(
                "Site not found.", details={"site_id": site_id}
            )
        return row

    def _get_finding_or_404(self, finding_id):
        row = self.db.query_one(
            "SELECT * FROM findings WHERE id = ?", (finding_id,)
        )
        if row is None:
            raise NotFoundError(
                "Finding not found.", details={"finding_id": finding_id}
            )
        return row

    # --------------------------------------------------------------- projects
    def create_project(self, body):
        require_fields(body, ["project_code", "project_name", "owner_name"])
        project_code = clean_str(body, "project_code", required=True)
        project_name = clean_str(body, "project_name", required=True)
        owner_name = clean_str(body, "owner_name", required=True)
        status = clean_str(body, "status", default=sm.DRAFT) or sm.DRAFT
        sm.validate_status(status)

        existing = self.db.query_one(
            "SELECT id FROM projects WHERE project_code = ?", (project_code,)
        )
        if existing is not None:
            raise ConflictError(
                "project_code already exists.",
                details={"project_code": project_code},
            )

        created_at = _now()
        conn = self.db.transaction()
        with conn:
            cur = conn.execute(
                """INSERT INTO projects
                   (project_code, project_name, owner_name, status, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (project_code, project_name, owner_name, status, created_at),
            )
            project_id = cur.lastrowid
            self._record_audit(
                conn, "project", project_id, "create",
                actor_name=owner_name, new_status=status,
            )
        return 201, self._get_project_or_404(project_id)

    def list_projects(self, query):
        clauses = []
        params = []
        status = query.get("status")
        if status:
            sm.validate_status(status)
            clauses.append("p.status = ?")
            params.append(status)
        region = query.get("region")
        if region:
            clauses.append(
                "p.id IN (SELECT project_id FROM sites WHERE region = ?)"
            )
            params.append(region)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.db.query_all(
            f"SELECT p.* FROM projects p {where} ORDER BY p.id DESC", params
        )
        # Attach a risk summary for the list view. Everything is read from
        # the DB (projects/sites/findings/audit), never computed client side.
        for row in rows:
            row["site_count"] = self.db.query_one(
                "SELECT COUNT(*) AS c FROM sites WHERE project_id = ?",
                (row["id"],),
            )["c"]
            summary = self._project_risk_summary(row["id"])
            row["risk_summary"] = summary
            # Keep the flat highest_risk_level for backward compatibility.
            row["highest_risk_level"] = summary["highest_risk_level"]

        min_risk = query.get("min_risk_level")
        if min_risk:
            sm.validate_risk_level(min_risk)
            threshold = sm.risk_weight(min_risk)
            rows = [
                r for r in rows
                if sm.risk_weight(r["highest_risk_level"]) >= threshold
            ]
        return 200, {"items": rows, "count": len(rows)}

    def _project_risk_summary(self, project_id):
        """Aggregate a project's active-finding risk across its sites.

        Archived findings are excluded from the counts. ``last_updated_at``
        includes archived-finding history so it reflects real activity.
        """
        findings = self.db.query_all(
            """SELECT f.risk_level, f.finding_status FROM findings f
               JOIN sites s ON f.site_id = s.id
               WHERE s.project_id = ? AND f.finding_status != ?""",
            (project_id, sm.ARCHIVED),
        )
        counts = {level: 0 for level in sm.RISK_LEVELS}
        highest = None
        highest_w = -1
        unreviewed = 0
        rejected = 0
        for f in findings:
            counts[f["risk_level"]] = counts.get(f["risk_level"], 0) + 1
            w = sm.risk_weight(f["risk_level"])
            if w > highest_w:
                highest_w, highest = w, f["risk_level"]
            if f["finding_status"] in self._UNREVIEWED:
                unreviewed += 1
            elif f["finding_status"] == sm.REJECTED:
                rejected += 1
        last = self.db.query_one(
            """SELECT MAX(ts) AS last_updated_at FROM (
                   SELECT f.reported_at AS ts FROM findings f
                   JOIN sites s ON f.site_id = s.id WHERE s.project_id = ?
                   UNION ALL
                   SELECT a.created_at AS ts FROM audit_events a
                   JOIN findings f ON a.entity_id = f.id
                   JOIN sites s ON f.site_id = s.id
                   WHERE a.entity_type = 'finding' AND s.project_id = ?
               )""",
            (project_id, project_id),
        )
        return {
            "open_finding_count": len(findings),
            "unreviewed_count": unreviewed,
            "rejected_count": rejected,
            "risk_counts": counts,
            "highest_risk_level": highest,
            "last_updated_at": last["last_updated_at"] if last else None,
        }

    def _project_highest_risk(self, project_id):
        summary = self._project_risk_summary(project_id)
        return summary["highest_risk_level"]

    # Statuses that mean "not yet concluded by a reviewer".
    _UNREVIEWED = (sm.DRAFT, sm.SUBMITTED, sm.REVIEWING)

    def _site_risk_summary(self, site_id):
        """Risk roll-up for one site, reading live from the DB.

        Counts exclude archived findings (评审只看在办项); the archived
        history itself stays queryable via the findings list on site detail.
        ``last_updated_at`` reflects the most recent activity across the
        site's findings and their audit events.
        """
        findings = self.db.query_all(
            """SELECT id, risk_level, finding_status, reported_at
               FROM findings WHERE site_id = ? AND finding_status != ?""",
            (site_id, sm.ARCHIVED),
        )
        counts = {level: 0 for level in sm.RISK_LEVELS}
        highest = None
        highest_w = -1
        unreviewed = 0
        rejected = 0
        for f in findings:
            counts[f["risk_level"]] = counts.get(f["risk_level"], 0) + 1
            w = sm.risk_weight(f["risk_level"])
            if w > highest_w:
                highest_w, highest = w, f["risk_level"]
            if f["finding_status"] in self._UNREVIEWED:
                unreviewed += 1
            elif f["finding_status"] == sm.REJECTED:
                rejected += 1

        # Latest activity: newest finding audit event on this site, else the
        # newest reported_at. Archived findings' history is included here so
        # the timestamp reflects real activity, even if archived rows are
        # excluded from the risk counts above.
        last = self.db.query_one(
            """SELECT MAX(ts) AS last_updated_at FROM (
                   SELECT reported_at AS ts FROM findings WHERE site_id = ?
                   UNION ALL
                   SELECT a.created_at AS ts FROM audit_events a
                   JOIN findings f ON a.entity_id = f.id
                   WHERE a.entity_type = 'finding' AND f.site_id = ?
               )""",
            (site_id, site_id),
        )
        return {
            "finding_count": len(findings),
            "unreviewed_count": unreviewed,
            "rejected_count": rejected,
            "risk_counts": counts,
            "highest_risk_level": highest,
            "last_updated_at": last["last_updated_at"] if last else None,
        }

    def get_project(self, project_id):
        project = self._get_project_or_404(project_id)
        return 200, project

    def transition_project_status(self, project_id, body):
        project = self._get_project_or_404(project_id)
        require_fields(body, ["target_status"])
        target = clean_str(body, "target_status", required=True)
        note = clean_str(body, "note")
        actor = clean_str(body, "actor_name") or project["owner_name"]
        sm.ensure_transition(project["status"], target)
        conn = self.db.transaction()
        with conn:
            conn.execute(
                "UPDATE projects SET status = ? WHERE id = ?",
                (target, project_id),
            )
            self._record_audit(
                conn, "project", project_id, "status_change",
                actor_name=actor, old_status=project["status"],
                new_status=target, note=note,
            )
        return 200, self._get_project_or_404(project_id)

    # ------------------------------------------------------------------ sites
    def create_site(self, body):
        require_fields(body, ["site_code", "site_name", "project_id"])
        project_id = body.get("project_id")
        if not isinstance(project_id, int):
            raise ValidationError(
                "project_id must be an integer.",
                details={"field": "project_id"},
            )
        self._get_project_or_404(project_id)
        site_code = clean_str(body, "site_code", required=True)
        site_name = clean_str(body, "site_name", required=True)
        address_text = clean_str(body, "address_text")
        region = clean_str(body, "region")

        existing = self.db.query_one(
            "SELECT id FROM sites WHERE project_id = ? AND site_code = ?",
            (project_id, site_code),
        )
        if existing is not None:
            raise ConflictError(
                "site_code already exists within this project.",
                details={"site_code": site_code, "project_id": project_id},
            )

        conn = self.db.transaction()
        with conn:
            cur = conn.execute(
                """INSERT INTO sites
                   (site_code, site_name, address_text, region, project_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (site_code, site_name, address_text, region, project_id),
            )
            site_id = cur.lastrowid
            self._record_audit(conn, "site", site_id, "create")
        return 201, self._get_site_or_404(site_id)

    def list_sites(self, query):
        clauses = []
        params = []
        project_id = query.get("project_id")
        if project_id:
            clauses.append("project_id = ?")
            params.append(int(project_id))
        region = query.get("region")
        if region:
            clauses.append("region = ?")
            params.append(region)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.db.query_all(
            f"SELECT * FROM sites {where} ORDER BY id", params
        )
        return 200, {"items": rows, "count": len(rows)}

    def get_site(self, site_id):
        site = self._get_site_or_404(site_id)
        return 200, site

    def project_site_risk(self, project_id):
        """Per-site risk breakdown for a project (excludes archived).

        Returns per site: observation count, unreviewed count, rejected
        count, highest risk level and last updated timestamp — the numbers
        a review meeting needs. Archived findings are excluded from the
        counts but their history remains visible on the site detail page.
        """
        self._get_project_or_404(project_id)
        sites = self.db.query_all(
            "SELECT * FROM sites WHERE project_id = ? ORDER BY id",
            (project_id,),
        )
        result = []
        for site in sites:
            summary = self._site_risk_summary(site["id"])
            result.append({
                "site_id": site["id"],
                "site_code": site["site_code"],
                "site_name": site["site_name"],
                "region": site["region"],
                **summary,
            })
        return 200, {"project_id": project_id, "items": result}

    # -------------------------------------------------------------- templates
    @staticmethod
    def _validate_site_items(site_items):
        """Validate the template site_items structure, raising on any issue.

        Enforces: must be a list; each entry an object with non-empty
        site_code and site_name; no duplicate site_code within the batch
        (which would violate the (project_id, site_code) uniqueness when the
        template is instantiated).
        """
        if not isinstance(site_items, list):
            raise ValidationError(
                "site_items must be a JSON array.",
                details={"field": "site_items"},
            )
        seen = set()
        for idx, item in enumerate(site_items):
            if not isinstance(item, dict):
                raise ValidationError(
                    "Each site_items entry must be an object.",
                    details={"index": idx},
                )
            code = item.get("site_code")
            name = item.get("site_name")
            if not code or not name:
                raise ValidationError(
                    "site_items entries require site_code and site_name.",
                    details={"index": idx},
                )
            if code in seen:
                raise ValidationError(
                    "site_items contains a duplicate site_code.",
                    details={"index": idx, "site_code": code},
                )
            seen.add(code)
        return site_items

    def create_template(self, body):
        require_fields(body, ["template_name"])
        template_name = clean_str(body, "template_name", required=True)
        default_region = clean_str(body, "default_region")
        site_items = self._validate_site_items(body.get("site_items", []))
        existing = self.db.query_one(
            "SELECT id FROM templates WHERE template_name = ?",
            (template_name,),
        )
        if existing is not None:
            raise ConflictError(
                "template_name already exists.",
                details={"template_name": template_name},
            )
        conn = self.db.transaction()
        with conn:
            cur = conn.execute(
                """INSERT INTO templates
                   (template_name, default_region, site_items, created_at)
                   VALUES (?, ?, ?, ?)""",
                (template_name, default_region, json.dumps(site_items),
                 _now()),
            )
            template_id = cur.lastrowid
        return 201, self._get_template(template_id)

    def _get_template(self, template_id):
        row = self.db.query_one(
            "SELECT * FROM templates WHERE id = ?", (template_id,)
        )
        if row is None:
            raise NotFoundError(
                "Template not found.", details={"template_id": template_id}
            )
        row["site_items"] = json.loads(row["site_items"])
        return row

    def list_templates(self, query):
        rows = self.db.query_all("SELECT * FROM templates ORDER BY id DESC")
        for row in rows:
            row["site_items"] = json.loads(row["site_items"])
        return 200, {"items": rows, "count": len(rows)}

    def get_template(self, template_id):
        return 200, self._get_template(template_id)

    def create_project_from_template(self, template_id, body):
        template = self._get_template(template_id)
        require_fields(body, ["project_code", "project_name", "owner_name"])
        project_code = clean_str(body, "project_code", required=True)
        project_name = clean_str(body, "project_name", required=True)
        owner_name = clean_str(body, "owner_name", required=True)
        override_region = clean_str(body, "region")

        if self.db.query_one(
            "SELECT id FROM projects WHERE project_code = ?", (project_code,)
        ):
            raise ConflictError(
                "project_code already exists.",
                details={"project_code": project_code},
            )

        # Re-validate the stored template structure defensively: even though
        # create_template guards it, a template could have been written by an
        # older code path. Any structural problem aborts before we touch the DB.
        site_items = self._validate_site_items(template["site_items"])

        region = override_region or template["default_region"]
        created_at = _now()
        # Everything below runs in one transaction so we never leave a
        # project with a partial set of sites. A duplicate site_code (raised
        # as an IntegrityError by the UNIQUE(project_id, site_code) index) or
        # any other failure rolls back the whole batch — the project row
        # included — leaving no half-built data behind.
        conn = self.db.transaction()
        try:
            with conn:
                cur = conn.execute(
                    """INSERT INTO projects
                       (project_code, project_name, owner_name, status,
                        created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (project_code, project_name, owner_name, sm.DRAFT,
                     created_at),
                )
                project_id = cur.lastrowid
                self._record_audit(
                    conn, "project", project_id, "create_from_template",
                    actor_name=owner_name, new_status=sm.DRAFT,
                    note=f"template:{template['template_name']}",
                )
                created_sites = []
                for item in site_items:
                    site_region = item.get("region") or region
                    scur = conn.execute(
                        """INSERT INTO sites
                           (site_code, site_name, address_text, region,
                            project_id)
                           VALUES (?, ?, ?, ?, ?)""",
                        (item["site_code"], item["site_name"],
                         item.get("address_text"), site_region, project_id),
                    )
                    site_id = scur.lastrowid
                    self._record_audit(conn, "site", site_id, "create")
                    created_sites.append(site_id)
        except sqlite3.IntegrityError as exc:
            # `with conn:` has already rolled back the transaction.
            raise ConflictError(
                "Failed to generate sites from template; batch rolled back.",
                details={"reason": str(exc)},
            )
        project = self._get_project_or_404(project_id)
        project["site_ids"] = created_sites
        project["site_count"] = len(created_sites)
        return 201, project

    # --------------------------------------------------------------- findings
    def _validate_finding_payload(self, body, require_site=True):
        fields = ["category", "description", "risk_level", "reported_by"]
        if require_site:
            fields.append("site_id")
        require_fields(body, fields)
        if require_site:
            site_id = body.get("site_id")
            if not isinstance(site_id, int):
                raise ValidationError(
                    "site_id must be an integer.",
                    details={"field": "site_id"},
                )
            self._get_site_or_404(site_id)
        category = clean_str(body, "category", required=True)
        description = clean_str(body, "description", required=True)
        risk_level = clean_str(body, "risk_level", required=True)
        sm.validate_risk_level(risk_level)
        reported_by = clean_str(body, "reported_by", required=True)
        return category, description, risk_level, reported_by

    def save_finding_draft(self, body):
        (category, description, risk_level,
         reported_by) = self._validate_finding_payload(body)
        site_id = body["site_id"]
        reported_at = _now()
        conn = self.db.transaction()
        with conn:
            cur = conn.execute(
                """INSERT INTO findings
                   (site_id, category, description, risk_level,
                    finding_status, reported_by, reported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (site_id, category, description, risk_level, sm.DRAFT,
                 reported_by, reported_at),
            )
            finding_id = cur.lastrowid
            self._record_audit(
                conn, "finding", finding_id, "draft_saved",
                actor_name=reported_by, new_status=sm.DRAFT,
            )
        return 201, self._get_finding_or_404(finding_id)

    def update_finding_draft(self, finding_id, body):
        finding = self._get_finding_or_404(finding_id)
        if finding["finding_status"] != sm.DRAFT:
            raise ConflictError(
                "Only draft findings can be edited.",
                details={"finding_status": finding["finding_status"]},
            )
        (category, description, risk_level,
         reported_by) = self._validate_finding_payload(body, require_site=False)
        conn = self.db.transaction()
        with conn:
            conn.execute(
                """UPDATE findings SET category = ?, description = ?,
                   risk_level = ?, reported_by = ? WHERE id = ?""",
                (category, description, risk_level, reported_by, finding_id),
            )
            self._record_audit(
                conn, "finding", finding_id, "draft_updated",
                actor_name=reported_by, new_status=sm.DRAFT,
            )
        return 200, self._get_finding_or_404(finding_id)

    def submit_finding(self, finding_id, body):
        finding = self._get_finding_or_404(finding_id)
        actor = clean_str(body or {}, "actor_name") or finding["reported_by"]
        note = clean_str(body or {}, "note")
        sm.ensure_transition(finding["finding_status"], sm.SUBMITTED)
        conn = self.db.transaction()
        with conn:
            conn.execute(
                "UPDATE findings SET finding_status = ? WHERE id = ?",
                (sm.SUBMITTED, finding_id),
            )
            self._record_audit(
                conn, "finding", finding_id, "submit", actor_name=actor,
                old_status=finding["finding_status"], new_status=sm.SUBMITTED,
                note=note,
            )
        return 200, self._get_finding_or_404(finding_id)

    def transition_finding(self, finding_id, body):
        finding = self._get_finding_or_404(finding_id)
        require_fields(body, ["target_status"])
        target = clean_str(body, "target_status", required=True)
        actor = clean_str(body, "actor_name")
        note = clean_str(body, "note")
        sm.ensure_transition(finding["finding_status"], target)
        conn = self.db.transaction()
        with conn:
            conn.execute(
                "UPDATE findings SET finding_status = ? WHERE id = ?",
                (target, finding_id),
            )
            self._record_audit(
                conn, "finding", finding_id, "status_change",
                actor_name=actor, old_status=finding["finding_status"],
                new_status=target, note=note,
            )
        return 200, self._get_finding_or_404(finding_id)

    def review_finding(self, finding_id, body):
        finding = self._get_finding_or_404(finding_id)
        require_fields(body, ["reviewer_name", "conclusion"])
        reviewer = clean_str(body, "reviewer_name", required=True)
        conclusion = clean_str(body, "conclusion", required=True)
        note = clean_str(body, "review_note")
        if conclusion not in ("accept", "reject", "needs_more_info"):
            raise ValidationError(
                "conclusion must be accept, reject or needs_more_info.",
                details={"conclusion": conclusion},
            )
        # Map the reviewer's conclusion onto a target lifecycle status.
        mapping = {
            "accept": sm.ACCEPTED,
            "reject": sm.REJECTED,
            "needs_more_info": sm.REVIEWING,
        }
        target = mapping[conclusion]
        current = finding["finding_status"]
        # Build the concrete hop-by-hop path so every intermediate status
        # change is auditable. Accepting/rejecting a *submitted* finding
        # implicitly passes through reviewing: submitted -> reviewing -> target.
        path = self._review_transition_path(current, target)
        # Validate each hop before mutating anything.
        step_from = current
        for step_to in path:
            sm.ensure_transition(step_from, step_to)
            step_from = step_to

        conn = self.db.transaction()
        with conn:
            conn.execute(
                """INSERT INTO reviews
                   (finding_id, reviewer_name, conclusion, review_note,
                    resulting_status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (finding_id, reviewer, conclusion, note, target, _now()),
            )
            step_from = current
            for step_to in path:
                conn.execute(
                    "UPDATE findings SET finding_status = ? WHERE id = ?",
                    (step_to, finding_id),
                )
                # One audit event per hop, each carrying actor / action /
                # old_status / new_status / note.
                self._record_audit(
                    conn, "finding", finding_id, "review",
                    actor_name=reviewer, old_status=step_from,
                    new_status=step_to, note=note or conclusion,
                )
                step_from = step_to
        result = self._get_finding_or_404(finding_id)
        result["review_conclusion"] = conclusion
        return 200, result

    @staticmethod
    def _review_transition_path(current, target):
        """Return the ordered list of status hops for a review conclusion.

        Accept/reject on a submitted finding walks through reviewing so the
        submitted -> reviewing and reviewing -> target hops are each audited.
        When target == current (e.g. needs_more_info while already
        reviewing) the path is empty: the review is recorded without a
        status change.
        """
        if target == current:
            return []
        if current == sm.SUBMITTED and target in (sm.ACCEPTED, sm.REJECTED):
            return [sm.REVIEWING, target]
        return [target]

    def list_findings(self, query):
        clauses = []
        params = []
        status = query.get("finding_status")
        if status:
            sm.validate_status(status)
            clauses.append("f.finding_status = ?")
            params.append(status)
        site_id = query.get("site_id")
        if site_id:
            clauses.append("f.site_id = ?")
            params.append(int(site_id))
        risk_level = query.get("risk_level")
        if risk_level:
            sm.validate_risk_level(risk_level)
            clauses.append("f.risk_level = ?")
            params.append(risk_level)
        project_id = query.get("project_id")
        if project_id:
            clauses.append(
                "f.site_id IN (SELECT id FROM sites WHERE project_id = ?)"
            )
            params.append(int(project_id))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.db.query_all(
            f"""SELECT f.*, s.site_code, s.site_name, s.region
                FROM findings f JOIN sites s ON f.site_id = s.id
                {where} ORDER BY f.id DESC""",
            params,
        )
        return 200, {"items": rows, "count": len(rows)}

    def get_finding(self, finding_id):
        return 200, self._get_finding_or_404(finding_id)

    def finding_timeline(self, finding_id):
        finding = self._get_finding_or_404(finding_id)
        # Each event carries a private ("_ts", "_seq") sort key: created_at
        # first, then a per-source id so multiple events written inside one
        # transaction (same second) keep their real chronological order.
        events = []

        # The finding itself is the first entry of its own timeline.
        events.append({
            "_ts": finding["reported_at"],
            "_seq": 0,
            "kind": "finding",
            "created_at": finding["reported_at"],
            "finding_id": finding["id"],
            "category": finding["category"],
            "description": finding["description"],
            "risk_level": finding["risk_level"],
            "finding_status": finding["finding_status"],
            "reported_by": finding["reported_by"],
        })

        audits = self.db.query_all(
            "SELECT * FROM audit_events WHERE entity_type = 'finding' "
            "AND entity_id = ? ORDER BY id",
            (finding_id,),
        )
        for a in audits:
            events.append({
                "_ts": a["created_at"],
                "_seq": a["id"],
                "kind": "audit",
                "created_at": a["created_at"],
                "action": a["action"],
                "actor_name": a["actor_name"],
                "old_status": a["old_status"],
                "new_status": a["new_status"],
                "note": a["note"],
            })
        reviews = self.db.query_all(
            "SELECT * FROM reviews WHERE finding_id = ? ORDER BY id",
            (finding_id,),
        )
        for r in reviews:
            events.append({
                "_ts": r["created_at"],
                "_seq": r["id"],
                "kind": "review",
                "created_at": r["created_at"],
                "reviewer_name": r["reviewer_name"],
                "conclusion": r["conclusion"],
                "review_note": r["review_note"],
                "resulting_status": r["resulting_status"],
            })
        attachments = self.db.query_all(
            "SELECT * FROM attachments WHERE linked_finding_id = ? "
            "ORDER BY id",
            (finding_id,),
        )
        for at in attachments:
            events.append({
                "_ts": at["created_at"],
                "_seq": at["id"],
                "kind": "attachment",
                "created_at": at["created_at"],
                "file_name": at["file_name"],
                "file_type": at["file_type"],
                "storage_note": at["storage_note"],
            })
        # Order by timestamp, then by the per-source id captured above so
        # events sharing a second stay in the order they were written.
        events.sort(key=lambda e: (e["_ts"], e["_seq"]))
        for e in events:
            del e["_ts"]
            del e["_seq"]
        return 200, {"finding_id": finding_id, "events": events}

    # ------------------------------------------------------------ attachments
    def create_attachment(self, body):
        require_fields(body, ["file_name", "file_type", "linked_finding_id"])
        finding_id = body.get("linked_finding_id")
        if not isinstance(finding_id, int):
            raise ValidationError(
                "linked_finding_id must be an integer.",
                details={"field": "linked_finding_id"},
            )
        self._get_finding_or_404(finding_id)
        file_name = clean_str(body, "file_name", required=True)
        file_type = clean_str(body, "file_type", required=True)
        storage_note = clean_str(body, "storage_note")
        conn = self.db.transaction()
        with conn:
            cur = conn.execute(
                """INSERT INTO attachments
                   (file_name, file_type, storage_note, linked_finding_id,
                    created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (file_name, file_type, storage_note, finding_id, _now()),
            )
            attachment_id = cur.lastrowid
            self._record_audit(
                conn, "finding", finding_id, "attachment_registered",
                note=file_name,
            )
        row = self.db.query_one(
            "SELECT * FROM attachments WHERE id = ?", (attachment_id,)
        )
        return 201, row

    def list_attachments(self, query):
        finding_id = query.get("linked_finding_id")
        if finding_id:
            rows = self.db.query_all(
                "SELECT * FROM attachments WHERE linked_finding_id = ? "
                "ORDER BY id",
                (int(finding_id),),
            )
        else:
            rows = self.db.query_all("SELECT * FROM attachments ORDER BY id")
        return 200, {"items": rows, "count": len(rows)}

    # ----------------------------------------------------------------- audit
    def list_audit_events(self, query):
        clauses = []
        params = []
        entity_type = query.get("entity_type")
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        entity_id = query.get("entity_id")
        if entity_id:
            clauses.append("entity_id = ?")
            params.append(int(entity_id))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.db.query_all(
            f"SELECT * FROM audit_events {where} ORDER BY id DESC", params
        )
        return 200, {"items": rows, "count": len(rows)}

    # --------------------------------------------------------- risk overview
    def risk_overview(self, query):
        """Aggregate risk snapshot to support review meetings.

        Archived findings are excluded so the figures reflect open work.
        """
        project_id = query.get("project_id")
        params = []
        project_filter = ""
        if project_id:
            self._get_project_or_404(int(project_id))
            project_filter = (
                " AND f.site_id IN (SELECT id FROM sites WHERE project_id = ?)"
            )
            params.append(int(project_id))

        by_risk = {level: 0 for level in sm.RISK_LEVELS}
        rows = self.db.query_all(
            f"""SELECT f.risk_level, COUNT(*) AS c FROM findings f
                WHERE f.finding_status != '{sm.ARCHIVED}'{project_filter}
                GROUP BY f.risk_level""",
            params,
        )
        for r in rows:
            # Only count known risk levels; unexpected values are ignored
            # here (and surfaced by the consistency self-check).
            if r["risk_level"] in by_risk:
                by_risk[r["risk_level"]] = r["c"]

        by_status = {}
        srows = self.db.query_all(
            f"""SELECT f.finding_status, COUNT(*) AS c FROM findings f
                WHERE 1=1{project_filter} GROUP BY f.finding_status""",
            params,
        )
        for r in srows:
            by_status[r["finding_status"]] = r["c"]

        open_total = sum(by_risk.values())
        return 200, {
            "project_id": int(project_id) if project_id else None,
            "open_findings_total": open_total,
            "by_risk_level": by_risk,
            "by_status": by_status,
        }

    # ---------------------------------------------------- consistency checks
    def consistency_checks(self, query):
        """Pre-delivery self-check for data drift across the schema.

        Reads projects/sites/findings/attachments/audit/templates and returns
        one result per check with pass status, issue count and issue detail.
        The overall response passes only when every check passes. All fields
        stay snake_case to match the rest of the API.
        """
        checks = [
            self._check_orphan_sites(),
            self._check_findings_missing_site(),
            self._check_status_audit_mismatch(),
            self._check_attachments_missing_finding(),
            self._check_duplicate_site_codes(),
            self._check_risk_overview_consistency(),
        ]
        total_issues = sum(c["issue_count"] for c in checks)
        return 200, {
            "passed": total_issues == 0,
            "total_issues": total_issues,
            "checked_at": _now(),
            "checks": checks,
        }

    @staticmethod
    def _check_result(name, description, issues):
        return {
            "check_name": name,
            "description": description,
            "passed": len(issues) == 0,
            "issue_count": len(issues),
            "issues": issues,
        }

    def _check_orphan_sites(self):
        rows = self.db.query_all(
            """SELECT s.id AS site_id, s.site_code, s.project_id
               FROM sites s
               LEFT JOIN projects p ON s.project_id = p.id
               WHERE p.id IS NULL ORDER BY s.id"""
        )
        return self._check_result(
            "orphan_sites",
            "Sites must reference an existing project.",
            rows,
        )

    def _check_findings_missing_site(self):
        rows = self.db.query_all(
            """SELECT f.id AS finding_id, f.site_id
               FROM findings f
               LEFT JOIN sites s ON f.site_id = s.id
               WHERE s.id IS NULL ORDER BY f.id"""
        )
        return self._check_result(
            "findings_missing_site",
            "Findings must reference an existing site.",
            rows,
        )

    def _check_status_audit_mismatch(self):
        # For each finding that has at least one status-bearing audit event,
        # the current finding_status must equal the newest such event's
        # new_status. Findings with no status audit yet are skipped.
        findings = self.db.query_all(
            "SELECT id, finding_status FROM findings ORDER BY id"
        )
        issues = []
        for f in findings:
            last = self.db.query_one(
                """SELECT new_status FROM audit_events
                   WHERE entity_type = 'finding' AND entity_id = ?
                     AND new_status IS NOT NULL
                   ORDER BY id DESC LIMIT 1""",
                (f["id"],),
            )
            if last is None:
                continue
            if last["new_status"] != f["finding_status"]:
                issues.append({
                    "finding_id": f["id"],
                    "finding_status": f["finding_status"],
                    "last_audit_status": last["new_status"],
                })
        return self._check_result(
            "status_audit_mismatch",
            "finding_status must match the newest status audit event.",
            issues,
        )

    def _check_attachments_missing_finding(self):
        rows = self.db.query_all(
            """SELECT a.id AS attachment_id, a.linked_finding_id
               FROM attachments a
               LEFT JOIN findings f ON a.linked_finding_id = f.id
               WHERE f.id IS NULL ORDER BY a.id"""
        )
        return self._check_result(
            "attachments_missing_finding",
            "Attachments must reference an existing finding.",
            rows,
        )

    def _check_duplicate_site_codes(self):
        rows = self.db.query_all(
            """SELECT project_id, site_code, COUNT(*) AS occurrences
               FROM sites
               GROUP BY project_id, site_code
               HAVING COUNT(*) > 1
               ORDER BY project_id, site_code"""
        )
        return self._check_result(
            "duplicate_site_codes",
            "site_code must be unique within a project.",
            rows,
        )

    def _check_risk_overview_consistency(self):
        # The risk_overview aggregate (open, non-archived findings by risk
        # level) must equal a direct count of the same detail rows.
        _, overview = self.risk_overview({})
        aggregate_total = overview["open_findings_total"]
        detail_total = self.db.query_one(
            "SELECT COUNT(*) AS c FROM findings WHERE finding_status != ?",
            (sm.ARCHIVED,),
        )["c"]
        issues = []
        if aggregate_total != detail_total:
            issues.append({
                "aggregate_open_total": aggregate_total,
                "detail_open_total": detail_total,
            })
        # Also verify each risk level bucket matches the detail count.
        for level in sm.RISK_LEVELS:
            detail = self.db.query_one(
                """SELECT COUNT(*) AS c FROM findings
                   WHERE finding_status != ? AND risk_level = ?""",
                (sm.ARCHIVED, level),
            )["c"]
            if overview["by_risk_level"].get(level, 0) != detail:
                issues.append({
                    "risk_level": level,
                    "aggregate_count": overview["by_risk_level"].get(level, 0),
                    "detail_count": detail,
                })
        return self._check_result(
            "risk_overview_consistency",
            "risk_overview aggregates must match detail counts.",
            issues,
        )
