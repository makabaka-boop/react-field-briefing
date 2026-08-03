def _setup_project_site(client):
    p = client.post("/api/v1/projects", json={
        "project_code": "P-VAL", "project_name": "Validation", "owner_name": "Owner",
    }).json()
    s = client.post("/api/v1/sites", json={
        "project_id": p["id"], "site_code": "S-VAL", "site_name": "Site",
        "address_text": "addr", "region": "North",
    }).json()
    return p, s


def _valid_draft(site_id, **overrides):
    data = {
        "site_id": site_id,
        "category": "safety",
        "description": "loose cable near panel",
        "risk_level": "high",
        "reported_by": "Alice",
    }
    data.update(overrides)
    return data


def test_draft_requires_all_fields(client):
    _, s = _setup_project_site(client)

    for missing in ["category", "description", "risk_level", "reported_by"]:
        payload = _valid_draft(s["id"])
        payload[missing] = ""
        r = client.post("/api/v1/findings/draft", json=payload)
        assert r.status_code == 422, f"{missing} should be required"
        body = r.json()
        assert set(body.keys()) == {"error_code", "message", "details"}
        assert body["message"]


def test_draft_rejects_invalid_risk_level(client):
    _, s = _setup_project_site(client)
    r = client.post("/api/v1/findings/draft", json=_valid_draft(s["id"], risk_level="urgent"))
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"]


def test_draft_save_success(client):
    _, s = _setup_project_site(client)
    r = client.post("/api/v1/findings/draft", json=_valid_draft(s["id"]))
    assert r.status_code == 201
    data = r.json()
    assert data["finding_status"] == "draft"
    assert data["category"] == "safety"
    assert data["risk_level"] == "high"


def test_submit_requires_actor(client):
    _, s = _setup_project_site(client)
    fid = client.post("/api/v1/findings/draft", json=_valid_draft(s["id"])).json()["id"]
    r = client.post(f"/api/v1/findings/{fid}/submit", json={"actor": ""})
    assert r.status_code == 422


def test_submit_success_and_audit_chain(client):
    _, s = _setup_project_site(client)
    fid = client.post("/api/v1/findings/draft", json=_valid_draft(s["id"])).json()["id"]

    r = client.post(f"/api/v1/findings/{fid}/submit", json={"actor": "Alice", "note": "ready"})
    assert r.status_code == 200
    assert r.json()["finding_status"] == "submitted"

    r = client.patch(f"/api/v1/findings/{fid}/status", json={
        "status": "reviewing", "actor": "Bob", "note": "taking this",
    })
    assert r.status_code == 200

    r = client.post("/api/v1/reviews", json={
        "finding_id": fid, "reviewer_name": "Carol",
        "conclusion": "accepted", "comment": "verified",
    })
    assert r.status_code == 201

    audits = client.get(f"/api/v1/audit?entity_type=finding&entity_id={fid}").json()
    actions = {(a["action"], a["from_status"], a["to_status"], a["actor"]) for a in audits}

    assert ("submitted", "draft", "submitted", "Alice") in actions
    assert ("status_changed", "submitted", "reviewing", "Bob") in actions
    assert ("status_changed", "reviewing", "accepted", "Carol") in actions

    for a in audits:
        if a["action"] == "status_changed":
            assert a["actor"]
            assert a["from_status"]
            assert a["to_status"]
            assert a["event_metadata"].get("note")


def test_invalid_status_transition_rejected(client):
    _, s = _setup_project_site(client)
    fid = client.post("/api/v1/findings/draft", json=_valid_draft(s["id"])).json()["id"]

    r = client.patch(f"/api/v1/findings/{fid}/status", json={"status": "accepted", "actor": "x"})
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "validation_error"


def test_invalid_target_status_rejected(client):
    _, s = _setup_project_site(client)
    fid = client.post("/api/v1/findings/draft", json=_valid_draft(s["id"])).json()["id"]
    r = client.patch(f"/api/v1/findings/{fid}/status", json={"status": "bogus", "actor": "x"})
    assert r.status_code == 422


def test_site_timeline_merges_and_sorts(client):
    _, s = _setup_project_site(client)

    f1 = client.post("/api/v1/findings/draft", json=_valid_draft(s["id"], category="first")).json()
    f2 = client.post("/api/v1/findings/draft", json=_valid_draft(s["id"], category="second", risk_level="low")).json()

    client.post("/api/v1/attachments", json={
        "file_name": "a.jpg", "file_type": "image/jpeg",
        "storage_note": "s3://a", "linked_finding_id": f1["id"],
    })
    client.post(f"/api/v1/findings/{f1['id']}/submit", json={"actor": "Alice"})
    client.patch(f"/api/v1/findings/{f1['id']}/status", json={"status": "reviewing", "actor": "Bob"})

    r = client.get(f"/api/v1/sites/{s['id']}/timeline")
    assert r.status_code == 200
    events = r.json()

    types = {e["event_type"] for e in events}
    assert "finding_reported" in types
    assert "attachment_registered" in types
    assert "audit_event" in types

    timestamps = [e["occurred_at"] for e in events if e["occurred_at"]]
    assert timestamps == sorted(timestamps, reverse=True)

    audit_events = [e for e in events if e["event_type"] == "audit_event"]
    transitions = [
        (e["details"]["from_status"], e["details"]["to_status"], e["details"]["action"])
        for e in audit_events
        if e["details"].get("from_status") or e["details"].get("to_status")
    ]
    assert ("draft", "submitted", "submitted") in transitions
    assert ("submitted", "reviewing", "status_changed") in transitions


def test_site_timeline_not_found(client):
    r = client.get("/api/v1/sites/9999/timeline")
    assert r.status_code == 404
    assert set(r.json().keys()) == {"error_code", "message", "details"}
