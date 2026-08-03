def test_overview_and_site_risks(client):
    p = client.post("/api/v1/projects", json={
        "project_code": "P-O", "project_name": "O", "owner_name": "O",
    }).json()
    s1 = client.post("/api/v1/sites", json={
        "project_id": p["id"], "site_code": "1", "site_name": "S1",
        "address_text": "", "region": "North",
    }).json()
    s2 = client.post("/api/v1/sites", json={
        "project_id": p["id"], "site_code": "2", "site_name": "S2",
        "address_text": "", "region": "South",
    }).json()
    for s, risk in [(s1, "low"), (s1, "high"), (s2, "critical")]:
        client.post("/api/v1/findings/draft", json={
            "site_id": s["id"], "category": "c", "description": "d",
            "risk_level": risk, "reported_by": "x",
        })

    r = client.get("/api/v1/overview")
    assert r.status_code == 200
    ov = r.json()
    assert ov["total_projects"] == 1
    assert ov["total_sites"] == 2
    assert ov["total_findings"] == 3
    assert ov["by_risk"]["high"] == 1
    assert ov["by_risk"]["critical"] == 1
    assert ov["by_region"]["North"] == 1

    r = client.get(f"/api/v1/projects/{p['id']}/site-risks")
    risks = r.json()
    by_site = {x["site_id"]: x for x in risks}
    assert by_site[s1["id"]]["highest_risk"] == "high"
    assert by_site[s2["id"]]["highest_risk"] == "critical"
    assert by_site[s1["id"]]["by_risk"]["low"] == 1


def test_audit_events_query(client):
    p = client.post("/api/v1/projects", json={
        "project_code": "P-A", "project_name": "A", "owner_name": "Eve",
    }).json()
    r = client.get("/api/v1/audit", params={"entity_type": "project"})
    assert r.status_code == 200
    events = r.json()
    assert any(e["action"] == "created" for e in events)

    r = client.get("/api/v1/audit", params={"entity_type": "project", "entity_id": p["id"]})
    assert len(r.json()) >= 1


def test_timeline(client):
    p = client.post("/api/v1/projects", json={
        "project_code": "P-TL", "project_name": "TL", "owner_name": "O",
    }).json()
    s = client.post("/api/v1/sites", json={
        "project_id": p["id"], "site_code": "STL", "site_name": "Site",
        "address_text": "", "region": "R",
    }).json()
    f = client.post("/api/v1/findings/draft", json={
        "site_id": s["id"], "category": "c", "description": "d",
        "risk_level": "high", "reported_by": "x",
    }).json()
    client.post(f"/api/v1/findings/{f['id']}/submit", json={"actor": "x"})
    client.post("/api/v1/attachments", json={
        "file_name": "f.txt", "file_type": "text/plain",
        "storage_note": "note", "linked_finding_id": f["id"],
    })
    client.patch(f"/api/v1/findings/{f['id']}/status", json={"status": "reviewing", "actor": "x"})
    client.post("/api/v1/reviews", json={
        "finding_id": f["id"], "reviewer_name": "R",
        "conclusion": "rejected", "comment": "no",
    })

    r = client.get(f"/api/v1/projects/{p['id']}/timeline")
    assert r.status_code == 200
    events = r.json()
    types = {e["event_type"] for e in events}
    assert "site_created" in types
    assert "finding_reported" in types
    assert "attachment_registered" in types
    assert "review_concluded" in types
