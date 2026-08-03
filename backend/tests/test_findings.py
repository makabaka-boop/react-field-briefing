def _setup(client):
    p = client.post("/api/v1/projects", json={
        "project_code": "P-F", "project_name": "F", "owner_name": "O",
    }).json()
    s = client.post("/api/v1/sites", json={
        "project_id": p["id"], "site_code": "S-F", "site_name": "Site",
        "address_text": "addr", "region": "West",
    }).json()
    return p, s


def test_finding_draft_submit_review_flow(client):
    _, s = _setup(client)

    r = client.post("/api/v1/findings/draft", json={
        "site_id": s["id"], "category": "safety", "description": "loose wire",
        "risk_level": "high", "reported_by": "Carol",
    })
    assert r.status_code == 201
    assert r.json()["finding_status"] == "draft"
    fid = r.json()["id"]

    r = client.patch(f"/api/v1/findings/{fid}/draft", json={"description": "loose cable"})
    assert r.status_code == 200
    assert r.json()["description"] == "loose cable"

    r = client.post(f"/api/v1/findings/{fid}/submit", json={"actor": "Carol"})
    assert r.status_code == 200
    assert r.json()["finding_status"] == "submitted"

    r = client.patch(f"/api/v1/findings/{fid}/status", json={"status": "reviewing", "actor": "Carol"})
    assert r.status_code == 200

    r = client.post("/api/v1/reviews", json={
        "finding_id": fid, "reviewer_name": "Dan",
        "conclusion": "accepted", "comment": "fixed",
    })
    assert r.status_code == 201
    assert r.json()["conclusion"] == "accepted"

    r = client.get(f"/api/v1/findings/{fid}")
    assert r.json()["finding_status"] == "accepted"


def test_finding_filters(client):
    _, s = _setup(client)
    for cat, risk, status_path in [
        ("env", "low", None),
        ("safety", "critical", "submitted"),
    ]:
        f = client.post("/api/v1/findings/draft", json={
            "site_id": s["id"], "category": cat, "description": "d",
            "risk_level": risk, "reported_by": "x",
        }).json()
        if status_path:
            client.post(f"/api/v1/findings/{f['id']}/submit", json={"actor": "x"})

    r = client.get("/api/v1/findings", params={"status": "submitted"})
    assert len(r.json()) == 1
    r = client.get("/api/v1/findings", params={"risk_level": "low"})
    assert len(r.json()) == 1


def test_attachment_metadata_registration(client):
    _, s = _setup(client)
    f = client.post("/api/v1/findings/draft", json={
        "site_id": s["id"], "category": "c", "description": "d",
        "risk_level": "low", "reported_by": "x",
    }).json()
    r = client.post("/api/v1/attachments", json={
        "file_name": "photo.jpg", "file_type": "image/jpeg",
        "storage_note": "s3://bucket/photo.jpg", "linked_finding_id": f["id"],
    })
    assert r.status_code == 201
    assert r.json()["file_name"] == "photo.jpg"

    r = client.get(f"/api/v1/attachments/by-finding/{f['id']}")
    assert len(r.json()) == 1


def test_attachment_missing_finding(client):
    r = client.post("/api/v1/attachments", json={
        "file_name": "x", "file_type": "", "storage_note": "", "linked_finding_id": 9999,
    })
    assert r.status_code == 404
    assert r.json()["error_code"] == "not_found"
