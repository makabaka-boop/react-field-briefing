"""End-to-end handler tests against an in-memory SQLite database.

Run with:  python -m unittest discover -s tests  (from backend/)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Database  # noqa: E402
from app.errors import (ApiError, ConflictError, InvalidTransitionError,  # noqa: E402
                        NotFoundError, ValidationError)
from app.handlers import Handlers  # noqa: E402
from app import state_machine as sm  # noqa: E402


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.h = Handlers(self.db)

    def tearDown(self):
        self.db.close()

    def _project(self, code="P-1"):
        _, p = self.h.create_project({
            "project_code": code, "project_name": "Bridge Survey",
            "owner_name": "Ada",
        })
        return p

    def _site(self, project_id, code="S-1", region="north"):
        _, s = self.h.create_site({
            "site_code": code, "site_name": "Pier A",
            "project_id": project_id, "region": region,
        })
        return s

    def _finding(self, site_id, risk="high"):
        _, f = self.h.save_finding_draft({
            "site_id": site_id, "category": "structural",
            "description": "Crack observed", "risk_level": risk,
            "reported_by": "Grace",
        })
        return f


class ProjectTests(BaseCase):
    def test_create_and_get(self):
        status, p = self.h.create_project({
            "project_code": "PC-9", "project_name": "N", "owner_name": "O",
        })
        self.assertEqual(status, 201)
        self.assertEqual(p["status"], "draft")
        self.assertEqual(p["project_code"], "PC-9")

    def test_duplicate_code_conflict(self):
        self._project("DUP")
        with self.assertRaises(ConflictError):
            self._project("DUP")

    def test_missing_fields(self):
        with self.assertRaises(ValidationError):
            self.h.create_project({"project_code": "X"})

    def test_list_filter_by_status(self):
        self._project("A")
        _, res = self.h.list_projects({"status": "draft"})
        self.assertEqual(res["count"], 1)
        _, res2 = self.h.list_projects({"status": "accepted"})
        self.assertEqual(res2["count"], 0)

    def test_project_status_transition(self):
        p = self._project()
        _, updated = self.h.transition_project_status(
            p["id"], {"target_status": "submitted", "actor_name": "Ada"}
        )
        self.assertEqual(updated["status"], "submitted")

    def test_invalid_project_transition(self):
        p = self._project()
        with self.assertRaises(InvalidTransitionError):
            self.h.transition_project_status(
                p["id"], {"target_status": "accepted"}
            )

    def test_get_missing_project(self):
        with self.assertRaises(NotFoundError):
            self.h.get_project(999)


class SiteTests(BaseCase):
    def test_create_site(self):
        p = self._project()
        status, s = self.h.create_site({
            "site_code": "SS-1", "site_name": "Gate", "project_id": p["id"],
            "region": "east",
        })
        self.assertEqual(status, 201)
        self.assertEqual(s["region"], "east")

    def test_site_requires_valid_project(self):
        with self.assertRaises(NotFoundError):
            self.h.create_site({
                "site_code": "X", "site_name": "Y", "project_id": 424,
            })

    def test_duplicate_site_code_in_project(self):
        p = self._project()
        self._site(p["id"], "S-DUP")
        with self.assertRaises(ConflictError):
            self._site(p["id"], "S-DUP")

    def test_filter_by_region(self):
        p = self._project()
        self._site(p["id"], "S-N", region="north")
        self._site(p["id"], "S-E", region="east")
        _, res = self.h.list_sites({"region": "north"})
        self.assertEqual(res["count"], 1)

    def test_project_site_risk(self):
        p = self._project()
        s = self._site(p["id"])
        self._finding(s["id"], risk="critical")
        _, risk = self.h.project_site_risk(p["id"])
        self.assertEqual(risk["items"][0]["highest_risk_level"], "critical")
        self.assertEqual(risk["items"][0]["finding_count"], 1)


class TemplateTests(BaseCase):
    def _template(self, name="T1"):
        _, t = self.h.create_template({
            "template_name": name, "default_region": "west",
            "site_items": [
                {"site_code": "A", "site_name": "Alpha"},
                {"site_code": "B", "site_name": "Beta", "region": "south"},
            ],
        })
        return t

    def test_create_template(self):
        t = self._template()
        self.assertEqual(len(t["site_items"]), 2)

    def test_template_site_items_must_be_list(self):
        with self.assertRaises(ValidationError):
            self.h.create_template({
                "template_name": "Bad", "site_items": {"a": 1},
            })

    def test_template_entry_requires_codes(self):
        with self.assertRaises(ValidationError):
            self.h.create_template({
                "template_name": "Bad2",
                "site_items": [{"site_name": "no code"}],
            })

    def test_create_project_from_template_batch_sites(self):
        t = self._template("TB")
        status, project = self.h.create_project_from_template(t["id"], {
            "project_code": "FT-1", "project_name": "From Template",
            "owner_name": "Owner",
        })
        self.assertEqual(status, 201)
        self.assertEqual(project["site_count"], 2)
        _, sites = self.h.list_sites({"project_id": project["id"]})
        self.assertEqual(sites["count"], 2)
        # default_region applied to entry lacking its own region
        regions = {s["site_code"]: s["region"] for s in sites["items"]}
        self.assertEqual(regions["A"], "west")
        self.assertEqual(regions["B"], "south")

    def test_template_project_rolls_back_on_dupe(self):
        t = self._template("TR")
        self.h.create_project_from_template(t["id"], {
            "project_code": "RB-1", "project_name": "x", "owner_name": "o",
        })
        before = self.h.list_sites({})[1]["count"]
        with self.assertRaises(ConflictError):
            self.h.create_project_from_template(t["id"], {
                "project_code": "RB-1", "project_name": "x", "owner_name": "o",
            })
        after = self.h.list_sites({})[1]["count"]
        self.assertEqual(before, after)  # no partial sites created

    def test_template_rejects_in_batch_duplicate_site_code(self):
        # A template whose site_items repeat a site_code would violate the
        # (project_id, site_code) uniqueness; reject it at template creation.
        with self.assertRaises(ValidationError):
            self.h.create_template({
                "template_name": "DupCodes",
                "site_items": [
                    {"site_code": "X", "site_name": "One"},
                    {"site_code": "X", "site_name": "Two"},
                ],
            })

    def test_template_project_rolls_back_project_row_too(self):
        # Force an IntegrityError mid-batch by pre-creating a project whose
        # sites collide with a template built via a raw insert (bypassing the
        # create_template guard) that contains duplicate codes.
        import json as _json
        conn = self.db.transaction()
        with conn:
            conn.execute(
                """INSERT INTO templates
                   (template_name, default_region, site_items, created_at)
                   VALUES (?, ?, ?, ?)""",
                ("Legacy", "west",
                 _json.dumps([
                     {"site_code": "D", "site_name": "One"},
                     {"site_code": "D", "site_name": "Two"},
                 ]), "2026-01-01T00:00:00Z"),
            )
        tpl_id = self.db.query_one(
            "SELECT id FROM templates WHERE template_name = 'Legacy'")["id"]
        projects_before = self.h.list_projects({})[1]["count"]
        # _validate_site_items catches the duplicate before any DB write.
        with self.assertRaises(ValidationError):
            self.h.create_project_from_template(tpl_id, {
                "project_code": "LG-1", "project_name": "x", "owner_name": "o",
            })
        projects_after = self.h.list_projects({})[1]["count"]
        self.assertEqual(projects_before, projects_after)  # project rolled back


class RiskSummaryTests(BaseCase):
    """Risk statistics: counting semantics and archived exclusion."""

    def setUp(self):
        super().setUp()
        self.p = self._project()
        self.s = self._site(self.p["id"], region="north")

    def test_site_summary_counts(self):
        # draft (unreviewed), submitted (unreviewed), rejected, accepted
        f_draft = self._finding(self.s["id"], risk="low")
        f_sub = self._finding(self.s["id"], risk="high")
        self.h.submit_finding(f_sub["id"], {})
        f_rej = self._finding(self.s["id"], risk="medium")
        self.h.submit_finding(f_rej["id"], {})
        self.h.review_finding(f_rej["id"], {
            "reviewer_name": "R", "conclusion": "reject"})
        _, risk = self.h.project_site_risk(self.p["id"])
        site = risk["items"][0]
        self.assertEqual(site["finding_count"], 3)
        self.assertEqual(site["unreviewed_count"], 2)  # draft + submitted
        self.assertEqual(site["rejected_count"], 1)
        self.assertEqual(site["highest_risk_level"], "high")
        self.assertIsNotNone(site["last_updated_at"])

    def test_archived_excluded_from_stats(self):
        f = self._finding(self.s["id"], risk="critical")
        _, risk = self.h.project_site_risk(self.p["id"])
        self.assertEqual(risk["items"][0]["finding_count"], 1)
        self.assertEqual(risk["items"][0]["highest_risk_level"], "critical")
        # archive it -> drops from counts and highest risk
        self.h.transition_finding(f["id"], {"target_status": "archived"})
        _, risk2 = self.h.project_site_risk(self.p["id"])
        self.assertEqual(risk2["items"][0]["finding_count"], 0)
        self.assertIsNone(risk2["items"][0]["highest_risk_level"])

    def test_archived_history_still_visible_on_site_detail(self):
        # Archived findings are excluded from stats but must remain queryable
        # (the site detail page lists them via finding_status filter).
        f = self._finding(self.s["id"], risk="high")
        self.h.transition_finding(f["id"], {"target_status": "archived"})
        _, listed = self.h.list_findings({
            "site_id": self.s["id"], "finding_status": "archived"})
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["items"][0]["id"], f["id"])

    def test_project_list_risk_summary(self):
        f = self._finding(self.s["id"], risk="high")
        self.h.submit_finding(f["id"], {})
        _, res = self.h.list_projects({})
        row = res["items"][0]
        self.assertIn("risk_summary", row)
        rs = row["risk_summary"]
        self.assertEqual(rs["open_finding_count"], 1)
        self.assertEqual(rs["unreviewed_count"], 1)
        self.assertEqual(rs["highest_risk_level"], "high")
        self.assertIsNotNone(rs["last_updated_at"])

    def test_project_list_filter_by_region(self):
        # second project without any site in 'north'
        _, p2 = self.h.create_project({
            "project_code": "P2", "project_name": "Other", "owner_name": "O"})
        self.h.create_site({
            "site_code": "S2", "site_name": "s2", "project_id": p2["id"],
            "region": "south"})
        _, res = self.h.list_projects({"region": "north"})
        codes = {r["project_code"] for r in res["items"]}
        self.assertIn(self.p["project_code"], codes)
        self.assertNotIn("P2", codes)

    def test_project_list_filter_by_min_risk(self):
        # p1 has a high finding; a second project has only low
        f = self._finding(self.s["id"], risk="high")
        _, p2 = self.h.create_project({
            "project_code": "P2", "project_name": "Other", "owner_name": "O"})
        s2 = self._site(p2["id"], code="S2", region="south")
        self._finding(s2["id"], risk="low")
        _, res = self.h.list_projects({"min_risk_level": "high"})
        codes = {r["project_code"] for r in res["items"]}
        self.assertIn(self.p["project_code"], codes)
        self.assertNotIn("P2", codes)


class FindingTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.p = self._project()
        self.s = self._site(self.p["id"])

    def test_draft_save_and_status(self):
        f = self._finding(self.s["id"])
        self.assertEqual(f["finding_status"], "draft")

    def test_invalid_risk_level(self):
        with self.assertRaises(ValidationError):
            self.h.save_finding_draft({
                "site_id": self.s["id"], "category": "c",
                "description": "d", "risk_level": "extreme",
                "reported_by": "r",
            })

    def test_missing_description_rejected(self):
        with self.assertRaises(ValidationError):
            self.h.save_finding_draft({
                "site_id": self.s["id"], "category": "c",
                "description": "   ", "risk_level": "low",
                "reported_by": "r",
            })

    def test_edit_only_draft(self):
        f = self._finding(self.s["id"])
        self.h.submit_finding(f["id"], {})
        with self.assertRaises(ConflictError):
            self.h.update_finding_draft(f["id"], {
                "category": "c", "description": "new", "risk_level": "low",
                "reported_by": "r",
            })

    def test_submit_and_review_accept(self):
        f = self._finding(self.s["id"])
        _, sub = self.h.submit_finding(f["id"], {"actor_name": "Grace"})
        self.assertEqual(sub["finding_status"], "submitted")
        _, rev = self.h.review_finding(f["id"], {
            "reviewer_name": "Rev", "conclusion": "accept",
            "review_note": "ok",
        })
        self.assertEqual(rev["finding_status"], "accepted")

    def test_review_reject(self):
        f = self._finding(self.s["id"])
        self.h.submit_finding(f["id"], {})
        _, rev = self.h.review_finding(f["id"], {
            "reviewer_name": "Rev", "conclusion": "reject",
        })
        self.assertEqual(rev["finding_status"], "rejected")

    def test_review_needs_more_info(self):
        f = self._finding(self.s["id"])
        self.h.submit_finding(f["id"], {})
        _, rev = self.h.review_finding(f["id"], {
            "reviewer_name": "Rev", "conclusion": "needs_more_info",
        })
        self.assertEqual(rev["finding_status"], "reviewing")

    def test_invalid_conclusion(self):
        f = self._finding(self.s["id"])
        self.h.submit_finding(f["id"], {})
        with self.assertRaises(ValidationError):
            self.h.review_finding(f["id"], {
                "reviewer_name": "R", "conclusion": "maybe",
            })

    def test_filter_by_status(self):
        f1 = self._finding(self.s["id"])
        self._finding(self.s["id"])
        self.h.submit_finding(f1["id"], {})
        _, res = self.h.list_findings({"finding_status": "submitted"})
        self.assertEqual(res["count"], 1)
        _, res2 = self.h.list_findings({"finding_status": "draft"})
        self.assertEqual(res2["count"], 1)

    def test_filter_by_project(self):
        self._finding(self.s["id"])
        _, res = self.h.list_findings({"project_id": self.p["id"]})
        self.assertEqual(res["count"], 1)

    def test_timeline_merges_events(self):
        f = self._finding(self.s["id"])
        self.h.create_attachment({
            "file_name": "photo.jpg", "file_type": "image/jpeg",
            "linked_finding_id": f["id"],
        })
        self.h.submit_finding(f["id"], {})
        self.h.review_finding(f["id"], {
            "reviewer_name": "R", "conclusion": "accept",
        })
        _, tl = self.h.finding_timeline(f["id"])
        kinds = {e["kind"] for e in tl["events"]}
        # the finding itself is the first-class opening entry
        self.assertIn("finding", kinds)
        self.assertIn("audit", kinds)
        self.assertIn("review", kinds)
        self.assertIn("attachment", kinds)
        self.assertEqual(tl["events"][0]["kind"], "finding")
        # sorted ascending by created_at
        times = [e["created_at"] for e in tl["events"]]
        self.assertEqual(times, sorted(times))
        # internal sort keys are stripped from the response
        self.assertNotIn("_ts", tl["events"][0])
        self.assertNotIn("_seq", tl["events"][0])

    def test_timeline_orders_multi_hop_review(self):
        # Even when several audit rows share the same second, the timeline
        # must present submit -> reviewing -> accepted in write order.
        f = self._finding(self.s["id"])
        self.h.submit_finding(f["id"], {"actor_name": "Grace"})
        self.h.review_finding(f["id"], {
            "reviewer_name": "Rev", "conclusion": "accept",
        })
        _, tl = self.h.finding_timeline(f["id"])
        audit_new = [e["new_status"] for e in tl["events"]
                     if e["kind"] == "audit"]
        self.assertEqual(
            audit_new, ["draft", "submitted", "reviewing", "accepted"]
        )


class ReviewAuditTests(BaseCase):
    """Every submitted->reviewing->accepted/rejected hop is audited."""

    def setUp(self):
        super().setUp()
        self.p = self._project()
        self.s = self._site(self.p["id"])

    def _audit_hops(self, finding_id):
        _, res = self.h.list_audit_events({
            "entity_type": "finding", "entity_id": finding_id,
        })
        # list is DESC by id; return (old, new) in chronological order
        review_events = [e for e in res["items"] if e["action"] == "review"]
        review_events.sort(key=lambda e: e["id"])
        return [(e["old_status"], e["new_status"], e["actor_name"],
                 e["note"]) for e in review_events]

    def test_accept_writes_two_hops(self):
        f = self._finding(self.s["id"])
        self.h.submit_finding(f["id"], {})
        _, rev = self.h.review_finding(f["id"], {
            "reviewer_name": "Rev", "conclusion": "accept",
            "review_note": "looks good",
        })
        self.assertEqual(rev["finding_status"], "accepted")
        hops = self._audit_hops(f["id"])
        # submitted -> reviewing, reviewing -> accepted
        self.assertEqual(
            [(h[0], h[1]) for h in hops],
            [("submitted", "reviewing"), ("reviewing", "accepted")],
        )
        # each hop carries actor and note
        for old, new, actor, note in hops:
            self.assertEqual(actor, "Rev")
            self.assertEqual(note, "looks good")

    def test_reject_writes_two_hops(self):
        f = self._finding(self.s["id"])
        self.h.submit_finding(f["id"], {})
        self.h.review_finding(f["id"], {
            "reviewer_name": "Rev", "conclusion": "reject",
        })
        hops = self._audit_hops(f["id"])
        self.assertEqual(
            [(h[0], h[1]) for h in hops],
            [("submitted", "reviewing"), ("reviewing", "rejected")],
        )

    def test_needs_more_info_then_accept(self):
        f = self._finding(self.s["id"])
        self.h.submit_finding(f["id"], {})
        # first move to reviewing explicitly
        _, r1 = self.h.review_finding(f["id"], {
            "reviewer_name": "Rev", "conclusion": "needs_more_info",
        })
        self.assertEqual(r1["finding_status"], "reviewing")
        # now accept from reviewing: single hop
        _, r2 = self.h.review_finding(f["id"], {
            "reviewer_name": "Rev", "conclusion": "accept",
        })
        self.assertEqual(r2["finding_status"], "accepted")
        hops = self._audit_hops(f["id"])
        self.assertEqual(
            [(h[0], h[1]) for h in hops],
            [("submitted", "reviewing"), ("reviewing", "accepted")],
        )

    def test_illegal_review_from_draft(self):
        # A draft finding cannot be reviewed (draft -> reviewing is illegal).
        f = self._finding(self.s["id"])
        with self.assertRaises(InvalidTransitionError):
            self.h.review_finding(f["id"], {
                "reviewer_name": "Rev", "conclusion": "accept",
            })


class AttachmentTests(BaseCase):
    def test_attachment_requires_finding(self):
        with self.assertRaises(NotFoundError):
            self.h.create_attachment({
                "file_name": "f", "file_type": "t", "linked_finding_id": 5,
            })

    def test_attachment_metadata_only(self):
        p = self._project()
        s = self._site(p["id"])
        f = self._finding(s["id"])
        status, a = self.h.create_attachment({
            "file_name": "report.pdf", "file_type": "application/pdf",
            "storage_note": "external drive", "linked_finding_id": f["id"],
        })
        self.assertEqual(status, 201)
        self.assertEqual(a["file_name"], "report.pdf")
        self.assertNotIn("file_content", a)


class AuditAndOverviewTests(BaseCase):
    def test_audit_events_recorded(self):
        p = self._project()
        _, res = self.h.list_audit_events({"entity_type": "project"})
        self.assertGreaterEqual(res["count"], 1)

    def test_risk_overview_excludes_archived(self):
        p = self._project()
        s = self._site(p["id"])
        f = self._finding(s["id"], risk="high")
        _, ov = self.h.risk_overview({"project_id": p["id"]})
        self.assertEqual(ov["by_risk_level"]["high"], 1)
        # archive the finding, then it drops from risk counts
        self.h.transition_finding(f["id"], {"target_status": "archived"})
        _, ov2 = self.h.risk_overview({"project_id": p["id"]})
        self.assertEqual(ov2["by_risk_level"]["high"], 0)
        self.assertEqual(ov2["open_findings_total"], 0)


class StateMachineTests(unittest.TestCase):
    def test_valid_and_invalid(self):
        self.assertTrue(sm.can_transition("draft", "submitted"))
        self.assertFalse(sm.can_transition("draft", "accepted"))
        with self.assertRaises(InvalidTransitionError):
            sm.ensure_transition("accepted", "draft")

    def test_unknown_status(self):
        with self.assertRaises(ValidationError):
            sm.validate_status("nope")


class ConsistencyCheckTests(BaseCase):
    """Pre-delivery data drift self-check."""

    def _all_pass(self, report):
        return {c["check_name"]: c for c in report["checks"]}

    def _seed(self, sql, params=()):
        # Raw insert that can bypass FK enforcement to simulate drifted data.
        conn = self.db.transaction()
        conn.execute("PRAGMA foreign_keys = OFF")
        with conn:
            conn.execute(sql, params)
        conn.execute("PRAGMA foreign_keys = ON")

    def test_all_checks_pass_on_clean_data(self):
        p = self._project()
        s = self._site(p["id"])
        f = self._finding(s["id"], risk="high")
        self.h.submit_finding(f["id"], {})
        _, report = self.h.consistency_checks({})
        self.assertTrue(report["passed"])
        self.assertEqual(report["total_issues"], 0)
        self.assertEqual(len(report["checks"]), 6)
        # snake_case fields present in response
        self.assertIn("checked_at", report)
        for c in report["checks"]:
            self.assertIn("check_name", c)
            self.assertIn("issue_count", c)
            self.assertTrue(c["passed"])

    def test_detects_orphan_site(self):
        self._seed(
            "INSERT INTO sites (site_code, site_name, project_id) "
            "VALUES ('X', 'orphan', 9999)"
        )
        _, report = self.h.consistency_checks({})
        checks = self._all_pass(report)
        self.assertFalse(report["passed"])
        self.assertEqual(checks["orphan_sites"]["issue_count"], 1)
        self.assertEqual(
            checks["orphan_sites"]["issues"][0]["project_id"], 9999
        )

    def test_detects_finding_missing_site(self):
        self._seed(
            "INSERT INTO findings (site_id, category, description, "
            "risk_level, finding_status, reported_by, reported_at) "
            "VALUES (9999, 'c', 'd', 'low', 'draft', 'r', '2026-01-01T00:00:00Z')"
        )
        _, report = self.h.consistency_checks({})
        checks = self._all_pass(report)
        self.assertEqual(checks["findings_missing_site"]["issue_count"], 1)

    def test_detects_status_audit_mismatch(self):
        p = self._project()
        s = self._site(p["id"])
        f = self._finding(s["id"])
        self.h.submit_finding(f["id"], {})
        # Corrupt the stored status so it no longer matches the last audit.
        self._seed(
            "UPDATE findings SET finding_status = 'accepted' WHERE id = ?",
            (f["id"],),
        )
        _, report = self.h.consistency_checks({})
        checks = self._all_pass(report)
        issue = checks["status_audit_mismatch"]
        self.assertEqual(issue["issue_count"], 1)
        self.assertEqual(issue["issues"][0]["finding_status"], "accepted")
        self.assertEqual(issue["issues"][0]["last_audit_status"], "submitted")

    def test_detects_attachment_missing_finding(self):
        self._seed(
            "INSERT INTO attachments (file_name, file_type, "
            "linked_finding_id, created_at) "
            "VALUES ('f.jpg', 'image/jpeg', 9999, '2026-01-01T00:00:00Z')"
        )
        _, report = self.h.consistency_checks({})
        checks = self._all_pass(report)
        self.assertEqual(
            checks["attachments_missing_finding"]["issue_count"], 1
        )

    def test_detects_duplicate_site_codes(self):
        p = self._project()
        # The live schema enforces UNIQUE(project_id, site_code); to simulate
        # drifted/legacy data we rebuild the sites table without that
        # constraint and insert a duplicate, then confirm the self-check
        # still flags it.
        conn = self.db.transaction()
        with conn:
            conn.execute("ALTER TABLE sites RENAME TO sites_old")
            conn.execute(
                """CREATE TABLE sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_code TEXT NOT NULL,
                    site_name TEXT NOT NULL,
                    address_text TEXT,
                    region TEXT,
                    project_id INTEGER NOT NULL
                )"""
            )
            conn.execute(
                "INSERT INTO sites (site_code, site_name, project_id) "
                "VALUES ('DUP', 'a', ?), ('DUP', 'b', ?)",
                (p["id"], p["id"]),
            )
        _, report = self.h.consistency_checks({})
        checks = self._all_pass(report)
        dup = checks["duplicate_site_codes"]
        self.assertEqual(dup["issue_count"], 1)
        self.assertEqual(dup["issues"][0]["site_code"], "DUP")
        self.assertEqual(dup["issues"][0]["occurrences"], 2)

    def test_detects_risk_overview_mismatch(self):
        # This check derives both numbers from the same table, so to force a
        # mismatch we insert a finding with an unknown risk_level: it counts
        # in the detail total but not in any known-level bucket.
        p = self._project()
        s = self._site(p["id"])
        self._seed(
            "INSERT INTO findings (site_id, category, description, "
            "risk_level, finding_status, reported_by, reported_at) "
            "VALUES (?, 'c', 'd', 'bogus', 'draft', 'r', '2026-01-01T00:00:00Z')",
            (s["id"],),
        )
        _, report = self.h.consistency_checks({})
        checks = self._all_pass(report)
        self.assertFalse(checks["risk_overview_consistency"]["passed"])
        self.assertGreaterEqual(
            checks["risk_overview_consistency"]["issue_count"], 1
        )


if __name__ == "__main__":
    unittest.main()
