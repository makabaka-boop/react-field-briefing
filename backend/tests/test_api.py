"""端到端 API 测试。

运行方式（在 backend/ 目录下）：
    python3 -m unittest discover tests -v

setUpClass 中以独立线程启动一个使用临时数据库文件的服务实例（APP_DB_PATH）。
"""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

from app.main import create_server


class ApiTestCase(unittest.TestCase):
    """按编号顺序执行的有状态端到端测试。"""

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="field_briefing_test_")
        os.environ["APP_DB_PATH"] = os.path.join(cls._tmpdir.name, "test.db")
        cls.server = create_server(port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = "http://127.0.0.1:%d" % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        os.environ.pop("APP_DB_PATH", None)
        cls._tmpdir.cleanup()

    # ------------------------------------------------------------------
    # 请求辅助
    # ------------------------------------------------------------------

    def api(self, method, path, body=None, raw_body=None):
        url = self.base_url + urllib.parse.quote(path, safe="/?=&")
        if raw_body is not None:
            data = raw_body
        elif body is not None:
            data = json.dumps(body).encode("utf-8")
        else:
            data = None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode("utf-8")
                return resp.status, json.loads(text) if text else None
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8")
            return exc.code, json.loads(text) if text else None

    # ------------------------------------------------------------------
    # 项目与模板
    # ------------------------------------------------------------------

    def test_01_create_project(self):
        status, data = self.api("POST", "/api/v1/projects", {
            "project_code": "P-100", "project_name": "一号项目", "owner_name": "张三",
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["project_code"], "P-100")
        self.assertEqual(data["project_name"], "一号项目")
        self.assertEqual(data["owner_name"], "张三")
        self.assertEqual(data["status"], "draft")
        self.assertTrue(data["created_at"])
        type(self).project_id = data["id"]

    def test_02_duplicate_project_code(self):
        status, data = self.api("POST", "/api/v1/projects", {
            "project_code": "P-100", "project_name": "重复项目", "owner_name": "张三",
        })
        self.assertEqual(status, 409)
        self.assertEqual(data["error_code"], "DUPLICATE_CODE")
        self.assertIn("message", data)
        self.assertIn("details", data)

    def test_03_missing_required_field(self):
        status, data = self.api("POST", "/api/v1/projects", {"project_code": "P-X"})
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")

    def test_04_create_site_template(self):
        status, data = self.api("POST", "/api/v1/site_templates", {
            "template_name": "标准两站点模板",
            "default_region": "华东",
            "site_items": [
                {"site_code": "A-01", "site_name": "Alpha 站点", "address_text": "地址A"},
                {"site_code": "B-01", "site_name": "Beta 站点"},
            ],
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["template_name"], "标准两站点模板")
        self.assertEqual(data["default_region"], "华东")
        self.assertIsInstance(data["site_items"], list)
        self.assertEqual(len(data["site_items"]), 2)
        type(self).template_id = data["id"]

    def test_05_template_invalid_site_items(self):
        status, data = self.api("POST", "/api/v1/site_templates", {
            "template_name": "坏模板", "site_items": [],
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")
        status, data = self.api("POST", "/api/v1/site_templates", {
            "template_name": "坏模板2", "site_items": [{"site_code": "X-01"}],
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")

    def test_06_create_project_from_template(self):
        status, data = self.api("POST", "/api/v1/projects/from_template", {
            "project_code": "P-200", "project_name": "模板项目",
            "owner_name": "李四", "template_id": self.template_id,
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["project_code"], "P-200")
        self.assertEqual(len(data["sites"]), 2)
        for site in data["sites"]:
            self.assertEqual(site["region"], "华东")
        type(self).tpl_project_id = data["id"]
        type(self).site_a_id = data["sites"][0]["id"]
        type(self).site_b_id = data["sites"][1]["id"]
        self.assertEqual(data["sites"][0]["site_code"], "A-01")
        self.assertEqual(data["sites"][0]["address_text"], "地址A")

    def test_07_from_template_not_found(self):
        status, data = self.api("POST", "/api/v1/projects/from_template", {
            "project_code": "P-201", "project_name": "x", "owner_name": "y",
            "template_id": 99999,
        })
        self.assertEqual(status, 404)
        self.assertEqual(data["error_code"], "TEMPLATE_NOT_FOUND")

    def test_08_get_project_detail(self):
        status, data = self.api("GET", "/api/v1/projects/%d" % self.tpl_project_id)
        self.assertEqual(status, 200)
        self.assertEqual(data["id"], self.tpl_project_id)
        self.assertEqual(len(data["sites"]), 2)

    def test_09_project_not_found(self):
        status, data = self.api("GET", "/api/v1/projects/99999")
        self.assertEqual(status, 404)
        self.assertEqual(data["error_code"], "PROJECT_NOT_FOUND")

    def test_10_list_projects_filter(self):
        status, data = self.api("GET", "/api/v1/projects?status=draft")
        self.assertEqual(status, 200)
        codes = [p["project_code"] for p in data]
        self.assertIn("P-100", codes)
        self.assertIn("P-200", codes)
        status, data = self.api("GET", "/api/v1/projects?status=archived")
        self.assertEqual(status, 200)
        self.assertEqual(data, [])

    # ------------------------------------------------------------------
    # 地点
    # ------------------------------------------------------------------

    def test_11_create_site(self):
        status, data = self.api("POST", "/api/v1/sites", {
            "site_code": "C-01", "site_name": "Gamma 站点",
            "region": "华北", "project_id": self.tpl_project_id,
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["site_code"], "C-01")
        self.assertEqual(data["region"], "华北")
        self.assertEqual(data["address_text"], "")
        type(self).site_c_id = data["id"]

    def test_12_create_site_project_not_found(self):
        status, data = self.api("POST", "/api/v1/sites", {
            "site_code": "C-02", "site_name": "x", "project_id": 99999,
        })
        self.assertEqual(status, 404)
        self.assertEqual(data["error_code"], "PROJECT_NOT_FOUND")

    def test_13_list_sites_filter(self):
        status, data = self.api("GET", "/api/v1/sites?region=华东")
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 2)
        status, data = self.api("GET", "/api/v1/sites?region=华北")
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["site_code"], "C-01")
        # 组合过滤
        status, data = self.api(
            "GET", "/api/v1/sites?project_id=%d&region=华北" % self.tpl_project_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 1)
        status, data = self.api(
            "GET", "/api/v1/sites?project_id=%d&region=华东" % self.tpl_project_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 2)

    def test_14_patch_site(self):
        status, data = self.api("PATCH", "/api/v1/sites/%d" % self.site_c_id, {
            "site_name": "Gamma 站点（改）", "address_text": "新地址",
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["site_name"], "Gamma 站点（改）")
        self.assertEqual(data["address_text"], "新地址")
        # 不允许的字段
        status, data = self.api("PATCH", "/api/v1/sites/%d" % self.site_c_id, {
            "site_code": "HACK",
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")

    def test_15_get_site_detail(self):
        status, data = self.api("GET", "/api/v1/sites/%d" % self.site_a_id)
        self.assertEqual(status, 200)
        self.assertEqual(data["id"], self.site_a_id)
        self.assertEqual(data["findings"], [])

    # ------------------------------------------------------------------
    # 观察项：草稿 -> 提交 -> 复核 -> 归档前流转
    # ------------------------------------------------------------------

    def test_16_create_finding_draft(self):
        status, data = self.api("POST", "/api/v1/findings", {
            "site_id": self.site_a_id, "category": "安全",
            "description": "护栏缺失", "risk_level": "high", "reported_by": "王五",
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["finding_status"], "draft")
        self.assertIsNone(data["reported_at"])
        self.assertEqual(data["risk_level"], "high")
        type(self).finding_id = data["id"]

    def test_17_create_finding_invalid_risk_level(self):
        status, data = self.api("POST", "/api/v1/findings", {
            "site_id": self.site_a_id, "category": "安全",
            "description": "x", "risk_level": "extreme", "reported_by": "王五",
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")

    def test_18_edit_draft_finding(self):
        status, data = self.api("PATCH", "/api/v1/findings/%d" % self.finding_id, {
            "category": "质量", "description": "护栏缺失，需整改",
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["category"], "质量")
        self.assertEqual(data["description"], "护栏缺失，需整改")
        self.assertEqual(data["finding_status"], "draft")

    def test_19_review_draft_conflict(self):
        # draft 状态直接 review -> 409
        status, data = self.api("POST", "/api/v1/findings/%d/review" % self.finding_id, {
            "reviewer_name": "赵六", "conclusion": "accepted",
        })
        self.assertEqual(status, 409)
        self.assertEqual(data["error_code"], "INVALID_STATE_TRANSITION")

    def test_20_submit_finding(self):
        status, data = self.api("POST", "/api/v1/findings/%d/submit" % self.finding_id)
        self.assertEqual(status, 200)
        self.assertEqual(data["finding_status"], "submitted")
        self.assertTrue(data["reported_at"])
        # 重复提交 -> 409
        status, data = self.api("POST", "/api/v1/findings/%d/submit" % self.finding_id)
        self.assertEqual(status, 409)
        self.assertEqual(data["error_code"], "INVALID_STATE_TRANSITION")

    def test_21_invalid_transition(self):
        # submitted 不能直接到 accepted
        status, data = self.api("POST", "/api/v1/findings/%d/transition" % self.finding_id, {
            "to_status": "accepted",
        })
        self.assertEqual(status, 409)
        self.assertEqual(data["error_code"], "INVALID_STATE_TRANSITION")
        # 非法目标状态值 -> 400
        status, data = self.api("POST", "/api/v1/findings/%d/transition" % self.finding_id, {
            "to_status": "nonsense",
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")

    def test_22_transition_to_reviewing(self):
        status, data = self.api("POST", "/api/v1/findings/%d/transition" % self.finding_id, {
            "to_status": "reviewing",
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["finding_status"], "reviewing")

    def test_23_review_accepted(self):
        status, data = self.api("POST", "/api/v1/findings/%d/review" % self.finding_id, {
            "reviewer_name": "赵六", "conclusion": "accepted", "comment": "同意",
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["conclusion"], "accepted")
        self.assertEqual(data["reviewer_name"], "赵六")
        self.assertEqual(data["comment"], "同意")
        # finding 状态已流转为 accepted
        status, rows = self.api(
            "GET", "/api/v1/findings?finding_status=accepted&project_id=%d" % self.tpl_project_id)
        self.assertEqual(status, 200)
        self.assertEqual([r["id"] for r in rows], [self.finding_id])
        # 复核记录列表
        status, rows = self.api("GET", "/api/v1/findings/%d/reviews" % self.finding_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["conclusion"], "accepted")

    def test_24_edit_non_draft_conflict(self):
        status, data = self.api("PATCH", "/api/v1/findings/%d" % self.finding_id, {
            "category": "安全",
        })
        self.assertEqual(status, 409)
        self.assertEqual(data["error_code"], "INVALID_STATE_TRANSITION")

    # ------------------------------------------------------------------
    # 附件与时间线
    # ------------------------------------------------------------------

    def test_25_register_attachment(self):
        status, data = self.api("POST", "/api/v1/attachments", {
            "file_name": "photo1.jpg", "file_type": "image/jpeg",
            "storage_note": "oss://bucket/photo1.jpg",
            "linked_finding_id": self.finding_id,
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["file_name"], "photo1.jpg")
        self.assertEqual(data["linked_finding_id"], self.finding_id)
        # finding 不存在 -> 404
        status, data = self.api("POST", "/api/v1/attachments", {
            "file_name": "x.png", "file_type": "image/png", "linked_finding_id": 99999,
        })
        self.assertEqual(status, 404)
        self.assertEqual(data["error_code"], "FINDING_NOT_FOUND")
        # 过滤
        status, rows = self.api(
            "GET", "/api/v1/attachments?linked_finding_id=%d" % self.finding_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["storage_note"], "oss://bucket/photo1.jpg")

    def test_26_finding_timeline(self):
        status, rows = self.api("GET", "/api/v1/findings/%d/timeline" % self.finding_id)
        self.assertEqual(status, 200)
        # 合并视图：首项为观察项本身，其余为审计事件（此时还未登记附件）
        self.assertEqual(rows[0]["item_type"], "finding")
        self.assertEqual(rows[0]["finding"]["id"], self.finding_id)
        events = [r for r in rows if r["item_type"] == "audit_event"]
        actions = [r["action"] for r in events]
        self.assertEqual(actions, [
            "finding_created", "finding_submitted", "status_transition", "finding_reviewed",
        ])
        self.assertEqual(events[0]["actor"], "王五")
        transition_event = events[2]
        self.assertEqual(transition_event["detail"]["from_status"], "submitted")
        self.assertEqual(transition_event["detail"]["to_status"], "reviewing")
        self.assertEqual(events[3]["detail"]["conclusion"], "accepted")
        for row in rows:
            self.assertTrue(row["created_at"])
        for row in events:
            self.assertIsInstance(row["detail"], dict)

    # ------------------------------------------------------------------
    # 风险视图与过滤
    # ------------------------------------------------------------------

    def test_27_more_findings_for_risk(self):
        status, data = self.api("POST", "/api/v1/findings", {
            "site_id": self.site_a_id, "category": "安全",
            "description": "深基坑无支护", "risk_level": "critical", "reported_by": "王五",
        })
        self.assertEqual(status, 201)
        type(self).finding2_id = data["id"]
        status, data = self.api("POST", "/api/v1/findings", {
            "site_id": self.site_b_id, "category": "环境",
            "description": "扬尘", "risk_level": "low", "reported_by": "孙七",
        })
        self.assertEqual(status, 201)
        type(self).finding3_id = data["id"]

    def test_28_risk_summary(self):
        status, data = self.api(
            "GET", "/api/v1/projects/%d/risk_summary" % self.tpl_project_id)
        self.assertEqual(status, 200)
        self.assertEqual(data["project_id"], self.tpl_project_id)
        self.assertEqual(data["total_sites"], 3)
        self.assertEqual(data["total_findings"], 3)
        self.assertEqual(data["by_risk_level"],
                         {"low": 1, "medium": 0, "high": 1, "critical": 1})
        self.assertEqual(data["by_status"], {
            "draft": 2, "submitted": 0, "reviewing": 0,
            "accepted": 1, "rejected": 0, "archived": 0,
        })

    def test_29_findings_filters(self):
        # finding_status 过滤
        status, rows = self.api("GET", "/api/v1/findings?finding_status=draft")
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 2)
        # project_id 过滤（JOIN sites），附带 site_name/site_code/project_id
        status, rows = self.api(
            "GET", "/api/v1/findings?project_id=%d" % self.tpl_project_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertIn("site_name", row)
            self.assertIn("site_code", row)
            self.assertEqual(row["project_id"], self.tpl_project_id)
        # 组合过滤
        status, rows = self.api(
            "GET", "/api/v1/findings?site_id=%d&risk_level=critical" % self.site_a_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], self.finding2_id)
        status, rows = self.api("GET", "/api/v1/findings?category=环境")
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], self.finding3_id)

    def test_30_risk_sites(self):
        status, rows = self.api(
            "GET", "/api/v1/projects/%d/risk_sites" % self.tpl_project_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 3)
        by_site = {r["site_id"]: r for r in rows}
        site_a = by_site[self.site_a_id]
        self.assertEqual(site_a["finding_count"], 2)
        self.assertEqual(site_a["max_risk_level"], "critical")
        self.assertEqual(site_a["risk_counts"],
                         {"low": 0, "medium": 0, "high": 1, "critical": 1})
        site_b = by_site[self.site_b_id]
        self.assertEqual(site_b["finding_count"], 1)
        self.assertEqual(site_b["max_risk_level"], "low")
        site_c = by_site[self.site_c_id]
        self.assertEqual(site_c["finding_count"], 0)
        self.assertIsNone(site_c["max_risk_level"])
        self.assertEqual(site_c["risk_counts"],
                         {"low": 0, "medium": 0, "high": 0, "critical": 0})

    # ------------------------------------------------------------------
    # 审计、错误处理与 CORS
    # ------------------------------------------------------------------

    def test_31_audit_events(self):
        status, rows = self.api(
            "GET", "/api/v1/audit_events?project_id=%d" % self.tpl_project_id)
        self.assertEqual(status, 200)
        actions = {r["action"] for r in rows}
        self.assertIn("project_created_from_template", actions)
        self.assertIn("site_created", actions)
        self.assertIn("finding_created", actions)
        self.assertIn("finding_submitted", actions)
        self.assertIn("status_transition", actions)
        self.assertIn("finding_reviewed", actions)
        self.assertIn("attachment_registered", actions)
        for row in rows:
            self.assertIsInstance(row["detail"], dict)
            self.assertEqual(row["project_id"], self.tpl_project_id)
        # entity_type + entity_id 过滤
        status, rows = self.api(
            "GET", "/api/v1/audit_events?entity_type=finding&entity_id=%d" % self.finding_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["entity_type"] == "finding" for r in rows))

    def test_32_invalid_json(self):
        status, data = self.api("POST", "/api/v1/projects", raw_body=b"{not valid json")
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "INVALID_JSON")

    def test_33_unknown_route(self):
        status, data = self.api("GET", "/api/v1/unknown_thing")
        self.assertEqual(status, 404)
        self.assertEqual(data["error_code"], "NOT_FOUND")

    def test_34_options_preflight(self):
        req = urllib.request.Request(self.base_url + "/api/v1/projects", method="OPTIONS")
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 204)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
            allow_methods = resp.headers.get("Access-Control-Allow-Methods") or ""
            for m in ("GET", "POST", "PATCH", "OPTIONS"):
                self.assertIn(m, allow_methods)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Headers"), "Content-Type")

    # ------------------------------------------------------------------
    # 严格校验、审计内容与合并时间线
    # ------------------------------------------------------------------

    def test_35_create_finding_empty_fields(self):
        base = {
            "site_id": self.site_a_id, "category": "安全",
            "description": "护栏缺失", "risk_level": "high", "reported_by": "王五",
        }
        for field in ("category", "description", "risk_level", "reported_by"):
            for empty_value in ("", "   "):
                body = dict(base)
                body[field] = empty_value
                status, data = self.api("POST", "/api/v1/findings", body)
                self.assertEqual(status, 400, "%s=%r should be rejected" % (field, empty_value))
                self.assertEqual(data["error_code"], "VALIDATION_ERROR")
                self.assertIn("message", data)
                self.assertIn("details", data)
        # 非字符串同样拒绝
        body = dict(base)
        body["category"] = 123
        status, data = self.api("POST", "/api/v1/findings", body)
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")

    def test_36_create_finding_invalid_risk_level_values(self):
        base = {
            "site_id": self.site_a_id, "category": "安全",
            "description": "x", "reported_by": "王五",
        }
        for bad_level in ("severe", "HIGH", " severe ", ""):
            body = dict(base)
            body["risk_level"] = bad_level
            status, data = self.api("POST", "/api/v1/findings", body)
            self.assertEqual(status, 400, "risk_level=%r should be rejected" % bad_level)
            self.assertEqual(data["error_code"], "VALIDATION_ERROR")
        # 合法值可通过（草稿保存成功）
        body = dict(base)
        body["risk_level"] = "medium"
        body["description"] = "临边防护不到位"
        status, data = self.api("POST", "/api/v1/findings", body)
        self.assertEqual(status, 201)
        self.assertEqual(data["finding_status"], "draft")
        type(self).finding4_id = data["id"]

    def test_37_patch_draft_rejects_empty_value(self):
        # finding4 仍是 draft
        status, data = self.api("PATCH", "/api/v1/findings/%d" % self.finding4_id, {
            "description": "   ",
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")
        # 正常编辑仍可用
        status, data = self.api("PATCH", "/api/v1/findings/%d" % self.finding4_id, {
            "description": "临边防护不到位，需加固",
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["description"], "临边防护不到位，需加固")

    def test_38_submit_and_transition_audit_with_note(self):
        # 提交成功
        status, data = self.api("POST", "/api/v1/findings/%d/submit" % self.finding4_id)
        self.assertEqual(status, 200)
        self.assertEqual(data["finding_status"], "submitted")
        self.assertTrue(data["reported_at"])
        # 非法状态跳转：submitted 不能直接 accepted
        status, data = self.api("POST", "/api/v1/findings/%d/transition" % self.finding4_id, {
            "to_status": "accepted",
        })
        self.assertEqual(status, 409)
        self.assertEqual(data["error_code"], "INVALID_STATE_TRANSITION")
        # submitted -> reviewing，携带操作者与说明
        status, data = self.api("POST", "/api/v1/findings/%d/transition" % self.finding4_id, {
            "to_status": "reviewing", "actor": "钱八", "note": "现场情况属实，进入复核",
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["finding_status"], "reviewing")
        status, rows = self.api(
            "GET", "/api/v1/audit_events?entity_type=finding&entity_id=%d" % self.finding4_id)
        self.assertEqual(status, 200)
        transition_events = [r for r in rows if r["action"] == "status_transition"]
        self.assertEqual(len(transition_events), 1)
        event = transition_events[0]
        self.assertEqual(event["actor"], "钱八")
        self.assertEqual(event["detail"]["from_status"], "submitted")
        self.assertEqual(event["detail"]["to_status"], "reviewing")
        self.assertEqual(event["detail"]["note"], "现场情况属实，进入复核")

    def test_39_review_audit_contains_status_and_note(self):
        status, data = self.api("POST", "/api/v1/findings/%d/review" % self.finding4_id, {
            "reviewer_name": "赵六", "conclusion": "rejected", "comment": "照片不足，补充后重报",
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["conclusion"], "rejected")
        status, rows = self.api(
            "GET", "/api/v1/audit_events?entity_type=finding&entity_id=%d" % self.finding4_id)
        self.assertEqual(status, 200)
        review_events = [r for r in rows if r["action"] == "finding_reviewed"]
        self.assertEqual(len(review_events), 1)
        event = review_events[0]
        self.assertEqual(event["actor"], "赵六")
        self.assertEqual(event["detail"]["from_status"], "reviewing")
        self.assertEqual(event["detail"]["to_status"], "rejected")
        self.assertEqual(event["detail"]["note"], "照片不足，补充后重报")
        self.assertEqual(event["detail"]["conclusion"], "rejected")

    def test_40_timeline_merged_and_sorted(self):
        # 给 finding4 登记附件
        status, data = self.api("POST", "/api/v1/attachments", {
            "file_name": "site-photo.png", "file_type": "image/png",
            "storage_note": "本地档案柜 A3", "linked_finding_id": self.finding4_id,
        })
        self.assertEqual(status, 201)
        status, rows = self.api("GET", "/api/v1/findings/%d/timeline" % self.finding4_id)
        self.assertEqual(status, 200)
        item_types = [r["item_type"] for r in rows]
        # 三类条目齐备
        self.assertIn("finding", item_types)
        self.assertIn("attachment", item_types)
        self.assertIn("audit_event", item_types)
        # 首项为观察项本身
        self.assertEqual(rows[0]["item_type"], "finding")
        self.assertEqual(rows[0]["finding"]["id"], self.finding4_id)
        # 附件元数据进入时间线
        attachment_items = [r for r in rows if r["item_type"] == "attachment"]
        self.assertEqual(len(attachment_items), 1)
        self.assertEqual(attachment_items[0]["attachment"]["file_name"], "site-photo.png")
        # 审计事件按序包含完整复核链路
        events = [r for r in rows if r["item_type"] == "audit_event"]
        self.assertEqual([e["action"] for e in events], [
            "finding_created", "finding_submitted", "status_transition", "finding_reviewed",
        ])
        # 整体按 created_at 非递减排序
        timestamps = [r["created_at"] for r in rows]
        self.assertEqual(timestamps, sorted(timestamps))

    # ------------------------------------------------------------------
    # 模板事务、风险统计口径与项目列表过滤
    # ------------------------------------------------------------------

    def test_41_from_template_duplicate_site_code_rollback(self):
        # 模板内地点编码重复 -> 409 且整批回滚
        status, data = self.api("POST", "/api/v1/site_templates", {
            "template_name": "重复编码模板",
            "default_region": "华南",
            "site_items": [
                {"site_code": "DUP-01", "site_name": "站点甲"},
                {"site_code": "DUP-01", "site_name": "站点乙"},
            ],
        })
        self.assertEqual(status, 201)
        dup_template_id = data["id"]
        status, data = self.api("POST", "/api/v1/projects/from_template", {
            "project_code": "P-DUP", "project_name": "回滚项目",
            "owner_name": "张三", "template_id": dup_template_id,
        })
        self.assertEqual(status, 409)
        self.assertEqual(data["error_code"], "DUPLICATE_CODE")
        # 项目与地点均未落库（无半成品数据）
        status, rows = self.api("GET", "/api/v1/projects")
        self.assertEqual(status, 200)
        self.assertNotIn("P-DUP", [p["project_code"] for p in rows])
        status, rows = self.api("GET", "/api/v1/sites?region=华南")
        self.assertEqual(status, 200)
        self.assertEqual(rows, [])
        # 审计事件也不得有该项目残留
        status, rows = self.api("GET", "/api/v1/audit_events?entity_type=project")
        self.assertEqual(status, 200)
        codes = [r["detail"].get("project_code") for r in rows]
        self.assertNotIn("P-DUP", codes)

    def test_42_from_template_invalid_site_items_rollback(self):
        # 直接写入结构非法的模板（绕过模板创建校验），按模板建项目应整体拒绝
        import json as _json
        from app.db import get_conn, utc_now
        conn = get_conn()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO site_templates (template_name, default_region, site_items,"
                    " created_at) VALUES (?, ?, ?, ?)",
                    ("坏结构模板", "西南",
                     _json.dumps([{"site_code": "X-01"}, "not-an-object"]), utc_now()),
                )
                bad_template_id = cur.lastrowid
        finally:
            conn.close()
        status, data = self.api("POST", "/api/v1/projects/from_template", {
            "project_code": "P-BAD", "project_name": "坏模板项目",
            "owner_name": "张三", "template_id": bad_template_id,
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")
        status, rows = self.api("GET", "/api/v1/projects")
        self.assertNotIn("P-BAD", [p["project_code"] for p in rows])

    def test_43_from_template_success_generates_sites(self):
        status, data = self.api("POST", "/api/v1/site_templates", {
            "template_name": "三站点模板",
            "default_region": "华南",
            "site_items": [
                {"site_code": "S-01", "site_name": "站点一"},
                {"site_code": "S-02", "site_name": "站点二", "address_text": "地址二"},
                {"site_name": "站点三"},
            ],
        })
        self.assertEqual(status, 201)
        status, data = self.api("POST", "/api/v1/projects/from_template", {
            "project_code": "P-300", "project_name": "成功项目",
            "owner_name": "李四", "template_id": data["id"],
        })
        self.assertEqual(status, 201)
        self.assertEqual(len(data["sites"]), 3)
        self.assertEqual([s["site_code"] for s in data["sites"]],
                         ["S-01", "S-02", "SITE-003"])
        for site in data["sites"]:
            self.assertEqual(site["region"], "华南")
        type(self).p300_id = data["id"]
        type(self).p300_site_id = data["sites"][0]["id"]

    def test_44_archive_excluded_from_risk_stats(self):
        # finding4（rejected, medium, site_a）归档
        status, data = self.api("POST", "/api/v1/findings/%d/transition" % self.finding4_id, {
            "to_status": "archived", "actor": "赵六", "note": "驳回后归档",
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["finding_status"], "archived")
        # 地点详情仍可查看归档历史
        status, data = self.api("GET", "/api/v1/sites/%d" % self.site_a_id)
        self.assertEqual(status, 200)
        archived = [f for f in data["findings"] if f["finding_status"] == "archived"]
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["id"], self.finding4_id)
        # risk_sites：site_a 统计排除 archived（剩 accepted/high + draft/critical）
        status, rows = self.api(
            "GET", "/api/v1/projects/%d/risk_sites" % self.tpl_project_id)
        self.assertEqual(status, 200)
        by_site = {r["site_id"]: r for r in rows}
        site_a = by_site[self.site_a_id]
        self.assertEqual(site_a["finding_count"], 2)
        self.assertEqual(site_a["unreviewed_count"], 1)   # draft 的 finding2
        self.assertEqual(site_a["rejected_count"], 0)     # 归档后不计入
        self.assertEqual(site_a["max_risk_level"], "critical")
        self.assertTrue(site_a["last_updated_at"])
        self.assertEqual(site_a["risk_counts"],
                         {"low": 0, "medium": 0, "high": 1, "critical": 1})
        # risk_summary：总量排除 archived，archived_count 单独返回
        status, data = self.api(
            "GET", "/api/v1/projects/%d/risk_summary" % self.tpl_project_id)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_findings"], 3)
        self.assertEqual(data["unreviewed_count"], 2)     # finding2 + finding3 均 draft
        self.assertEqual(data["rejected_count"], 0)
        self.assertEqual(data["archived_count"], 1)
        self.assertTrue(data["last_updated_at"])
        self.assertEqual(data["by_risk_level"],
                         {"low": 1, "medium": 0, "high": 1, "critical": 1})
        self.assertEqual(data["by_status"]["archived"], 0)
        self.assertEqual(data["by_status"]["accepted"], 1)
        self.assertEqual(data["by_status"]["draft"], 2)

    def test_45_project_list_risk_summary_and_filters(self):
        # 给 P-300 增加一条 high 观察项，便于过滤断言
        status, data = self.api("POST", "/api/v1/findings", {
            "site_id": self.p300_site_id, "category": "安全",
            "description": "临时用电乱接", "risk_level": "high", "reported_by": "孙七",
        })
        self.assertEqual(status, 201)
        # 列表携带风险摘要与区域
        status, rows = self.api("GET", "/api/v1/projects")
        self.assertEqual(status, 200)
        by_code = {p["project_code"]: p for p in rows}
        tpl = by_code["P-200"]
        self.assertEqual(tpl["risk_summary"]["total_findings"], 3)
        self.assertEqual(tpl["risk_summary"]["unreviewed_count"], 2)
        self.assertEqual(tpl["risk_summary"]["rejected_count"], 0)
        self.assertEqual(tpl["risk_summary"]["max_risk_level"], "critical")
        self.assertTrue(tpl["risk_summary"]["last_updated_at"])
        self.assertEqual(sorted(tpl["regions"]), ["华东", "华北"])
        p300 = by_code["P-300"]
        self.assertEqual(p300["risk_summary"]["max_risk_level"], "high")
        self.assertEqual(p300["regions"], ["华南"])
        empty = by_code["P-100"]
        self.assertEqual(empty["risk_summary"]["total_findings"], 0)
        self.assertIsNone(empty["risk_summary"]["max_risk_level"])
        # region 过滤
        status, rows = self.api("GET", "/api/v1/projects?region=华北")
        self.assertEqual(status, 200)
        self.assertEqual([p["project_code"] for p in rows], ["P-200"])
        status, rows = self.api("GET", "/api/v1/projects?region=华南")
        self.assertEqual([p["project_code"] for p in rows], ["P-300"])
        # max_risk_level 过滤
        status, rows = self.api("GET", "/api/v1/projects?max_risk_level=critical")
        self.assertEqual([p["project_code"] for p in rows], ["P-200"])
        status, rows = self.api("GET", "/api/v1/projects?max_risk_level=high")
        self.assertEqual([p["project_code"] for p in rows], ["P-300"])
        status, rows = self.api("GET", "/api/v1/projects?max_risk_level=low")
        self.assertEqual(rows, [])
        # 组合过滤与非法值
        status, rows = self.api(
            "GET", "/api/v1/projects?region=华南&max_risk_level=high")
        self.assertEqual([p["project_code"] for p in rows], ["P-300"])
        status, data = self.api("GET", "/api/v1/projects?max_risk_level=severe")
        self.assertEqual(status, 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")

    # ------------------------------------------------------------------
    # 一致性自检与 snake_case 校验
    # ------------------------------------------------------------------

    def test_46_consistency_checks_pass(self):
        status, data = self.api("GET", "/api/v1/consistency_checks")
        self.assertEqual(status, 200)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_issues"], 0)
        codes = [c["check_code"] for c in data["checks"]]
        self.assertEqual(codes, [
            "orphan_sites", "findings_without_site", "status_audit_mismatch",
            "orphan_attachments", "duplicate_site_codes", "risk_summary_mismatch",
        ])
        for check in data["checks"]:
            self.assertTrue(check["passed"])
            self.assertEqual(check["issue_count"], 0)
            self.assertEqual(check["issues"], [])
            self.assertTrue(check["check_name"])

    def test_47_consistency_checks_detect_and_recover(self):
        # 通过原始连接（默认不启用外键约束）注入漂移数据
        import sqlite3 as _sqlite3
        raw = _sqlite3.connect(os.environ["APP_DB_PATH"])
        raw.row_factory = _sqlite3.Row
        try:
            now = "2026-08-02T00:00:00.000Z"
            cur = raw.execute(
                "INSERT INTO sites (site_code, site_name, project_id) VALUES (?, ?, ?)",
                ("ORPHAN-S", "孤儿地点", 99999))
            orphan_site_id = cur.lastrowid
            cur = raw.execute(
                "INSERT INTO findings (site_id, category, description, risk_level,"
                " finding_status, reported_by, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, 'draft', ?, ?, ?)",
                (99999, "安全", "孤儿观察项", "low", "测试", now, now))
            orphan_finding_id = cur.lastrowid
            cur = raw.execute(
                "INSERT INTO attachments (file_name, file_type, linked_finding_id, created_at)"
                " VALUES (?, ?, ?, ?)",
                ("orphan.jpg", "image/jpeg", 99999, now))
            orphan_attachment_id = cur.lastrowid
            # 非法风险等级 -> 风险统计与明细不一致
            cur = raw.execute(
                "INSERT INTO findings (site_id, category, description, risk_level,"
                " finding_status, reported_by, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, 'draft', ?, ?, ?)",
                (self.p300_site_id, "安全", "漂移风险等级", "severe", "测试", now, now))
            drift_finding_id = cur.lastrowid
            # 直接改状态（无审计事件）-> 状态与最后一条审计事件不一致
            raw.execute("UPDATE findings SET finding_status = 'submitted' WHERE id = ?",
                        (self.finding3_id,))
            raw.commit()

            status, data = self.api("GET", "/api/v1/consistency_checks")
            self.assertEqual(status, 200)
            self.assertFalse(data["passed"])
            self.assertEqual(data["total_issues"], 5)
            by_code = {c["check_code"]: c for c in data["checks"]}
            self.assertFalse(by_code["orphan_sites"]["passed"])
            self.assertEqual(by_code["orphan_sites"]["issues"][0]["site_id"], orphan_site_id)
            self.assertEqual(by_code["orphan_sites"]["issues"][0]["project_id"], 99999)
            self.assertFalse(by_code["findings_without_site"]["passed"])
            self.assertEqual(
                by_code["findings_without_site"]["issues"][0]["finding_id"],
                orphan_finding_id)
            self.assertFalse(by_code["orphan_attachments"]["passed"])
            self.assertEqual(
                by_code["orphan_attachments"]["issues"][0]["attachment_id"],
                orphan_attachment_id)
            mismatch = by_code["status_audit_mismatch"]
            self.assertFalse(mismatch["passed"])
            issue = mismatch["issues"][0]
            self.assertEqual(issue["finding_id"], self.finding3_id)
            self.assertEqual(issue["finding_status"], "submitted")
            self.assertEqual(issue["expected_status"], "draft")
            self.assertEqual(issue["last_action"], "finding_created")
            risk = by_code["risk_summary_mismatch"]
            self.assertFalse(risk["passed"])
            self.assertEqual(risk["issues"][0]["project_id"], self.p300_id)
            self.assertEqual(risk["issues"][0]["invalid_risk_levels"], ["severe"])
            # 未被注入的检查保持通过
            self.assertTrue(by_code["duplicate_site_codes"]["passed"])
        finally:
            raw.execute("DELETE FROM sites WHERE id = ?", (orphan_site_id,))
            raw.execute("DELETE FROM findings WHERE id IN (?, ?)",
                        (orphan_finding_id, drift_finding_id))
            raw.execute("DELETE FROM attachments WHERE id = ?", (orphan_attachment_id,))
            raw.execute("UPDATE findings SET finding_status = 'draft' WHERE id = ?",
                        (self.finding3_id,))
            raw.commit()
            raw.close()
        # 清理后恢复全部通过
        status, data = self.api("GET", "/api/v1/consistency_checks")
        self.assertEqual(status, 200)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_issues"], 0)

    def test_48_responses_stay_snake_case(self):
        import re
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")

        def walk(value, path=""):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertRegex(key, pattern, "key %r at %s" % (key, path or "$"))
                    walk(item, "%s.%s" % (path, key))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, "%s[%d]" % (path, index))

        for path in ("/api/v1/consistency_checks", "/api/v1/projects",
                     "/api/v1/projects/%d/risk_sites" % self.tpl_project_id,
                     "/api/v1/projects/%d/risk_summary" % self.tpl_project_id,
                     "/api/v1/findings/%d/timeline" % self.finding_id):
            status, data = self.api("GET", path)
            self.assertEqual(status, 200, path)
            walk(data)


if __name__ == "__main__":
    unittest.main()
