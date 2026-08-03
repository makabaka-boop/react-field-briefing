from app.core.database import SessionLocal
from app.models.all_models import Attachment, Finding, Site


def _seed_clean(client):
    p = client.post("/api/v1/projects", json={
        "project_code": "P-CLEAN", "project_name": "Clean", "owner_name": "O",
    }).json()
    s = client.post("/api/v1/sites", json={
        "project_id": p["id"], "site_code": "C-1", "site_name": "Site",
        "address_text": "", "region": "North",
    }).json()
    client.post("/api/v1/findings/draft", json={
        "site_id": s["id"], "category": "safety", "description": "ok",
        "risk_level": "low", "reported_by": "Alice",
    })
    return p, s


def test_consistency_passes_on_clean_data(client):
    _seed_clean(client)
    r = client.get("/api/v1/consistency")
    assert r.status_code == 200
    body = r.json()

    assert body["passed"] is True
    assert body["total_checks"] == 6
    assert body["failed_checks"] == 0
    assert body["total_issues"] == 0

    check_names = {c["check_name"] for c in body["checks"]}
    assert check_names == {
        "orphan_sites",
        "orphan_findings",
        "orphan_attachments",
        "status_audit_drift",
        "template_duplicate_site_codes",
        "overview_consistency",
    }
    for c in body["checks"]:
        assert set(c.keys()) == {"check_name", "description", "passed", "issue_count", "issues"}
        assert c["passed"] is True
        assert c["issue_count"] == 0


def test_consistency_reports_orphan_finding(client):
    _seed_clean(client)
    db = SessionLocal()
    try:
        orphan = Finding(site_id=999999, category="x", description="x",
                         risk_level="low", finding_status="draft", reported_by="x")
        db.add(orphan)
        db.commit()
    finally:
        db.close()

    body = client.get("/api/v1/consistency").json()
    assert body["passed"] is False
    check = next(c for c in body["checks"] if c["check_name"] == "orphan_findings")
    assert check["passed"] is False
    assert check["issue_count"] == 1
    assert check["issues"][0]["site_id"] == 999999


def test_consistency_reports_orphan_attachment(client):
    p, s = _seed_clean(client)
    f = client.post("/api/v1/findings/draft", json={
        "site_id": s["id"], "category": "c", "description": "d",
        "risk_level": "low", "reported_by": "x",
    }).json()
    client.post("/api/v1/attachments", json={
        "file_name": "a.txt", "file_type": "text/plain",
        "storage_note": "n", "linked_finding_id": f["id"],
    })
    db = SessionLocal()
    try:
        db.add(Attachment(file_name="ghost", file_type="", storage_note="", linked_finding_id=888888))
        db.commit()
    finally:
        db.close()

    body = client.get("/api/v1/consistency").json()
    check = next(c for c in body["checks"] if c["check_name"] == "orphan_attachments")
    assert check["issue_count"] == 1
    assert check["issues"][0]["linked_finding_id"] == 888888


def test_consistency_reports_template_duplicate_codes(client):
    client.post("/api/v1/templates", json={
        "template_name": "Dup", "default_region": "",
        "site_items": [
            {"site_code": "D-1", "site_name": "A"},
            {"site_code": "D-1", "site_name": "B"},
        ],
    })
    body = client.get("/api/v1/consistency").json()
    check = next(c for c in body["checks"] if c["check_name"] == "template_duplicate_site_codes")
    assert check["passed"] is False
    assert check["issue_count"] == 1
    assert check["issues"][0]["site_code"] == "D-1"


def test_snake_case_fields_in_consistency_response(client):
    _seed_clean(client)
    body = client.get("/api/v1/consistency").json()
    top_keys = set(body.keys())
    assert top_keys == {"passed", "total_checks", "failed_checks", "total_issues", "checks"}
    for c in body["checks"]:
        for key in c.keys():
            assert "_" in key or key in {"passed", "issues", "description"}


def test_risk_summary_response_uses_snake_case(client):
    p, _ = _seed_clean(client)
    body = client.get(f"/api/v1/projects/{p['id']}/risk-summary").json()
    assert "project_id" in body
    assert "total_sites" in body
    assert "total_findings" in body
    assert "unreviewed_count" in body
    assert "rejected_count" in body
    assert "highest_risk" in body
    assert "last_updated_at" in body
    assert "sites" in body
    for s in body["sites"]:
        assert "site_id" in s and "site_code" in s and "site_name" in s
        assert "total_findings" in s and "unreviewed_count" in s
        assert "rejected_count" in s and "highest_risk" in s
