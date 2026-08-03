def _make_project_site(client, code="P-RISK", region="North"):
    p = client.post("/api/v1/projects", json={
        "project_code": code, "project_name": "Risk", "owner_name": "Owner",
    }).json()
    s = client.post("/api/v1/sites", json={
        "project_id": p["id"], "site_code": f"{code}-S1", "site_name": "Site 1",
        "address_text": "", "region": region,
    }).json()
    return p, s


def _finding(client, site_id, risk, status_path=None):
    f = client.post("/api/v1/findings/draft", json={
        "site_id": site_id, "category": "safety", "description": "desc",
        "risk_level": risk, "reported_by": "Alice",
    }).json()
    if status_path:
        for step in status_path:
            if step == "submit":
                client.post(f"/api/v1/findings/{f['id']}/submit", json={"actor": "Alice"})
            elif step == "review":
                client.patch(f"/api/v1/findings/{f['id']}/status",
                             json={"status": "reviewing", "actor": "Bob"})
            elif step == "accept":
                client.post("/api/v1/reviews", json={
                    "finding_id": f["id"], "reviewer_name": "Carol",
                    "conclusion": "accepted", "comment": "ok",
                })
            elif step == "reject":
                client.post("/api/v1/reviews", json={
                    "finding_id": f["id"], "reviewer_name": "Carol",
                    "conclusion": "rejected", "comment": "no",
                })
            elif step == "archive":
                client.patch(f"/api/v1/findings/{f['id']}/status",
                             json={"status": "archived", "actor": "Bob"})
    return f


def test_risk_summary_counts_and_excludes_archived(client):
    p, s = _make_project_site(client)

    _finding(client, s["id"], "high", ["submit", "review", "accept"])
    _finding(client, s["id"], "medium", ["submit", "review", "reject"])
    _finding(client, s["id"], "low", None)
    _finding(client, s["id"], "critical", ["submit", "review", "accept", "archive"])

    r = client.get(f"/api/v1/projects/{p['id']}/risk-summary")
    assert r.status_code == 200
    summary = r.json()

    assert summary["total_findings"] == 3
    assert summary["unreviewed_count"] == 1
    assert summary["rejected_count"] == 1
    assert summary["highest_risk"] == "high"
    assert summary["last_updated_at"]

    site = summary["sites"][0]
    assert site["total_findings"] == 3
    assert site["unreviewed_count"] == 1
    assert site["rejected_count"] == 1
    assert site["highest_risk"] == "high"
    assert site["last_updated_at"]


def test_project_list_has_risk_summary_columns(client):
    p, s = _make_project_site(client, code="P-LIST")
    _finding(client, s["id"], "critical", ["submit", "review", "accept"])

    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    items = r.json()
    mine = [x for x in items if x["id"] == p["id"]][0]
    assert "highest_risk" in mine
    assert "total_findings" in mine
    assert "unreviewed_count" in mine
    assert "rejected_count" in mine
    assert "last_updated_at" in mine
    assert mine["highest_risk"] == "critical"
    assert mine["total_findings"] == 1


def test_project_list_filter_by_highest_risk(client):
    p1, s1 = _make_project_site(client, code="P-LOW", region="North")
    _finding(client, s1["id"], "low", None)

    p2, s2 = _make_project_site(client, code="P-HIGH", region="South")
    _finding(client, s2["id"], "critical", None)

    r = client.get("/api/v1/projects", params={"highest_risk": "high"})
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()}
    assert p2["id"] in ids
    assert p1["id"] not in ids


def test_project_list_filter_by_region(client):
    p1, _ = _make_project_site(client, code="P-NORTH", region="North")
    p2, _ = _make_project_site(client, code="P-SOUTH", region="South")

    r = client.get("/api/v1/projects", params={"region": "North"})
    ids = {x["id"] for x in r.json()}
    assert p1["id"] in ids
    assert p2["id"] not in ids


def test_invalid_highest_risk_filter(client):
    r = client.get("/api/v1/projects", params={"highest_risk": "extreme"})
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"]


def test_archived_findings_still_visible_in_site_timeline(client):
    p, s = _make_project_site(client)
    f = _finding(client, s["id"], "high", ["submit", "review", "accept", "archive"])

    r = client.get(f"/api/v1/sites/{s['id']}/timeline")
    assert r.status_code == 200
    events = r.json()
    finding_events = [e for e in events if e["event_type"] == "finding_reported"]
    assert any(e["entity_id"] == f["id"] for e in finding_events)


def _make_template(client, items):
    return client.post("/api/v1/templates", json={
        "template_name": "T", "default_region": "East", "site_items": items,
    }).json()


def test_from_template_success_creates_all_sites_in_one_txn(client):
    tpl = _make_template(client, [
        {"site_code": "BATCH-1", "site_name": "One"},
        {"site_code": "BATCH-2", "site_name": "Two", "address_text": "addr"},
    ])
    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-BATCH", "project_name": "Batch", "owner_name": "Bob",
        "template_id": tpl["id"],
    })
    assert r.status_code == 201
    body = r.json()
    assert body["total_sites"] == 2
    sites = client.get("/api/v1/sites", params={"project_id": body["project_id"]}).json()
    assert {s["site_code"] for s in sites} == {"BATCH-1", "BATCH-2"}


def test_from_template_rolls_back_on_duplicate_site_code(client):
    tpl = _make_template(client, [
        {"site_code": "DUP-1", "site_name": "One"},
        {"site_code": "DUP-1", "site_name": "Two"},
    ])
    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-DUP", "project_name": "Dup", "owner_name": "Bob",
        "template_id": tpl["id"],
    })
    assert r.status_code == 422
    body = r.json()
    assert "duplicate" in body["message"].lower() or "DUP-1" in body["message"]

    projects = client.get("/api/v1/projects").json()
    assert all(p["project_code"] != "P-DUP" for p in projects)
    sites = client.get("/api/v1/sites").json()
    assert all(s["site_code"] != "DUP-1" for s in sites)


def test_from_template_rolls_back_on_invalid_structure(client):
    tpl = _make_template(client, [
        {"site_name": "Missing code"},
    ])
    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-BAD", "project_name": "Bad", "owner_name": "Bob",
        "template_id": tpl["id"],
    })
    assert r.status_code == 422
    projects = client.get("/api/v1/projects").json()
    assert all(p["project_code"] != "P-BAD" for p in projects)


def test_from_template_rejects_empty_site_items(client):
    tpl = _make_template(client, [])
    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-EMPTY", "project_name": "Empty", "owner_name": "Bob",
        "template_id": tpl["id"],
    })
    assert r.status_code == 422
