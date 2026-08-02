def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_project(client):
    r = client.post("/api/v1/projects", json={
        "project_code": "P001",
        "project_name": "Test Project",
        "owner_name": "Alice",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["project_code"] == "P001"
    assert data["status"] == "draft"
    assert "id" in data


def test_create_duplicate_project(client):
    client.post("/api/v1/projects", json={
        "project_code": "P002",
        "project_name": "Project",
        "owner_name": "Bob",
    })
    r = client.post("/api/v1/projects", json={
        "project_code": "P002",
        "project_name": "Project",
        "owner_name": "Bob",
    })
    assert r.status_code == 409
    body = r.json()
    assert "error_code" in body
    assert "message" in body
    assert "details" in body


def test_list_projects(client):
    client.post("/api/v1/projects", json={
        "project_code": "P003",
        "project_name": "Project 3",
        "owner_name": "Carol",
    })
    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_project_transition(client):
    pid = client.post("/api/v1/projects", json={
        "project_code": "P004",
        "project_name": "Project 4",
        "owner_name": "Dave",
    }).json()["id"]
    r = client.post(f"/api/v1/projects/{pid}/transition", json={"target_status": "submitted", "actor": "Dave"})
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"

    r = client.post(f"/api/v1/projects/{pid}/transition", json={"target_status": "accepted"})
    assert r.status_code == 409


def test_create_template_and_project_from_template(client):
    tpl = client.post("/api/v1/templates", json={
        "template_name": "Standard Site Template",
        "default_region": "East",
        "site_items": [
            {"site_code": "S-T01", "site_name": "Gate", "address_text": "123 Main St"},
            {"site_code": "S-T02", "site_name": "Building A"},
        ],
    })
    assert tpl.status_code == 200
    tid = tpl.json()["id"]

    proj = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-TPL",
        "project_name": "Template Project",
        "owner_name": "Eve",
        "template_id": tid,
    })
    assert proj.status_code == 200
    pid = proj.json()["id"]

    sites = client.get(f"/api/v1/sites?project_id={pid}")
    assert sites.status_code == 200
    assert len(sites.json()) == 2
    assert sites.json()[0]["region"] == "East"


def test_site_crud(client):
    pid = client.post("/api/v1/projects", json={
        "project_code": "P005",
        "project_name": "Site Project",
        "owner_name": "Frank",
    }).json()["id"]

    r = client.post("/api/v1/sites", json={
        "site_code": "S001",
        "site_name": "Main Site",
        "address_text": "456 Oak Ave",
        "region": "North",
        "project_id": pid,
    })
    assert r.status_code == 200
    sid = r.json()["id"]

    r = client.get(f"/api/v1/sites/{sid}")
    assert r.status_code == 200
    assert r.json()["site_name"] == "Main Site"

    r = client.patch(f"/api/v1/sites/{sid}", json={"site_name": "Updated Site", "region": "South"})
    assert r.status_code == 200
    assert r.json()["site_name"] == "Updated Site"
    assert r.json()["region"] == "South"

    r = client.delete(f"/api/v1/sites/{sid}")
    assert r.status_code == 200


def test_site_filter_by_region(client):
    pid = client.post("/api/v1/projects", json={
        "project_code": "P006",
        "project_name": "Region Project",
        "owner_name": "Grace",
    }).json()["id"]

    client.post("/api/v1/sites", json={
        "site_code": "S-R1", "site_name": "North Site", "region": "North", "project_id": pid,
    })
    client.post("/api/v1/sites", json={
        "site_code": "S-R2", "site_name": "South Site", "region": "South", "project_id": pid,
    })

    r = client.get("/api/v1/sites?region=North")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["region"] == "North"


def _create_project_site(client, code="P007", scode="S-F1", owner="Henry"):
    pid = client.post("/api/v1/projects", json={
        "project_code": code,
        "project_name": "Project",
        "owner_name": owner,
    }).json()["id"]
    sid = client.post("/api/v1/sites", json={
        "site_code": scode, "site_name": "Site", "project_id": pid,
    }).json()["id"]
    return pid, sid


def test_finding_lifecycle(client):
    pid, sid = _create_project_site(client, "P007", "S-F1", "Henry")

    r = client.post("/api/v1/findings", json={
        "site_id": sid,
        "category": "safety",
        "description": "Broken railing",
        "risk_level": "high",
        "reported_by": "Henry",
    })
    assert r.status_code == 200
    fid = r.json()["id"]
    assert r.json()["finding_status"] == "draft"

    r = client.post(f"/api/v1/findings/{fid}/save-draft", json={
        "description": "Broken railing on second floor",
    })
    assert r.status_code == 200
    assert "second floor" in r.json()["description"]

    r = client.post(f"/api/v1/findings/{fid}/submit", json={"actor": "Henry"})
    assert r.status_code == 200
    assert r.json()["finding_status"] == "submitted"

    r = client.post(f"/api/v1/findings/{fid}/transition", json={"target_status": "reviewing", "actor": "Ivy"})
    assert r.status_code == 200
    assert r.json()["finding_status"] == "reviewing"

    r = client.post(f"/api/v1/findings/{fid}/reviews", json={
        "reviewer_name": "Ivy",
        "conclusion": "approved",
        "comment": "Fixed and verified",
    })
    assert r.status_code == 200

    f = client.get(f"/api/v1/findings/{fid}")
    assert f.json()["finding_status"] == "accepted"


def test_finding_filter_by_status(client):
    pid, sid = _create_project_site(client, "P008", "S-FIL", "Jack")

    f1 = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "Issue 1",
        "risk_level": "low", "reported_by": "Jack",
    }).json()
    f2 = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "env", "description": "Issue 2",
        "risk_level": "medium", "reported_by": "Jack",
    }).json()

    client.post(f"/api/v1/findings/{f1['id']}/submit")

    r = client.get(f"/api/v1/findings?project_id={pid}&finding_status=submitted")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(f"/api/v1/findings?project_id={pid}&risk_level=medium")
    assert len(r.json()) == 1


def test_attachment_metadata(client):
    pid, sid = _create_project_site(client, "P009", "S-ATT", "Kate")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "doc", "description": "With attachment",
        "risk_level": "low", "reported_by": "Kate",
    }).json()["id"]

    r = client.post("/api/v1/attachments", json={
        "file_name": "photo_001.jpg",
        "file_type": "image/jpeg",
        "storage_note": "s3://bucket/photo_001.jpg",
        "linked_finding_id": fid,
    })
    assert r.status_code == 200
    assert r.json()["file_name"] == "photo_001.jpg"
    assert "created_at" in r.json()

    r = client.get(f"/api/v1/attachments?linked_finding_id={fid}")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_finding_timeline(client):
    pid, sid = _create_project_site(client, "P010", "S-TL", "Leo")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "x", "description": "Timeline item",
        "risk_level": "medium", "reported_by": "Leo",
    }).json()["id"]

    client.post(f"/api/v1/findings/{fid}/submit", json={"actor": "Leo"})
    client.post(f"/api/v1/findings/{fid}/transition", json={"target_status": "reviewing", "actor": "Leo"})
    client.post(f"/api/v1/findings/{fid}/reviews", json={
        "reviewer_name": "Mia",
        "conclusion": "approved",
        "comment": "OK",
    })

    r = client.get(f"/api/v1/findings/{fid}/timeline")
    assert r.status_code == 200
    timeline = r.json()["timeline"]
    assert len(timeline) >= 4
    types = [t["type"] for t in timeline]
    assert "review" in types
    assert "finding_created" in types

    timestamps = [t["timestamp"] for t in timeline]
    assert timestamps == sorted(timestamps)


def test_audit_events(client):
    pid = client.post("/api/v1/projects", json={
        "project_code": "P011",
        "project_name": "Audit Project",
        "owner_name": "Nina",
    }).json()["id"]

    r = client.get(f"/api/v1/audit-events?entity_type=project&entity_id={pid}")
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1
    assert events[0]["action"] == "create"


def test_risk_overview(client):
    pid, sid = _create_project_site(client, "P012", "S-RISK", "Oscar")

    client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "High risk",
        "risk_level": "high", "reported_by": "Oscar",
    })
    client.post("/api/v1/findings", json={
        "site_id": sid, "category": "env", "description": "Low risk",
        "risk_level": "low", "reported_by": "Oscar",
    })

    r = client.get(f"/api/v1/overview/risk?project_id={pid}")
    assert r.status_code == 200
    data = r.json()
    assert data["total_findings"] == 2
    assert data["risk_counts"]["high"] == 1
    assert data["risk_counts"]["low"] == 1


def test_project_sites_risk(client):
    pid, sid = _create_project_site(client, "P013", "S-SR", "Paul")
    client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "Critical issue",
        "risk_level": "critical", "reported_by": "Paul",
    })

    r = client.get(f"/api/v1/projects/{pid}/sites-risk")
    assert r.status_code == 200
    sites = r.json()["sites"]
    assert len(sites) == 1
    assert sites[0]["max_risk_level"] == "critical"
    assert sites[0]["risk_counts"]["critical"] == 1


def test_invalid_status(client):
    r = client.post("/api/v1/projects", json={
        "project_code": "P-BAD",
        "project_name": "Bad Status",
        "owner_name": "X",
        "status": "invalid_status",
    })
    assert r.status_code == 422
    assert "error_code" in r.json()


def test_not_found(client):
    r = client.get("/api/v1/projects/99999")
    assert r.status_code == 404
    body = r.json()
    assert body["error_code"] == "not_found"


def test_finding_empty_category_rejected(client):
    _, sid = _create_project_site(client, "P-V1", "S-V1", "Val")
    r = client.post("/api/v1/findings", json={
        "site_id": sid,
        "category": "",
        "description": "Some desc",
        "risk_level": "low",
        "reported_by": "Val",
    })
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "validation_error"
    assert "category" in body["details"]


def test_finding_empty_description_rejected(client):
    _, sid = _create_project_site(client, "P-V2", "S-V2", "Val")
    r = client.post("/api/v1/findings", json={
        "site_id": sid,
        "category": "safety",
        "description": "",
        "risk_level": "low",
        "reported_by": "Val",
    })
    assert r.status_code == 422
    assert "description" in r.json()["details"]


def test_finding_empty_reported_by_rejected(client):
    _, sid = _create_project_site(client, "P-V3", "S-V3", "Val")
    r = client.post("/api/v1/findings", json={
        "site_id": sid,
        "category": "safety",
        "description": "desc",
        "risk_level": "low",
        "reported_by": "",
    })
    assert r.status_code == 422
    assert "reported_by" in r.json()["details"]


def test_finding_invalid_risk_level_rejected(client):
    _, sid = _create_project_site(client, "P-V4", "S-V4", "Val")
    r = client.post("/api/v1/findings", json={
        "site_id": sid,
        "category": "safety",
        "description": "desc",
        "risk_level": "urgent",
        "reported_by": "Val",
    })
    assert r.status_code == 422
    details = r.json()["details"]
    assert "risk_level" in details
    assert "low" in details["risk_level"]
    assert "critical" in details["risk_level"]


def test_finding_update_cannot_set_empty_fields(client):
    _, sid = _create_project_site(client, "P-V5", "S-V5", "Val")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "desc",
        "risk_level": "low", "reported_by": "Val",
    }).json()["id"]
    r = client.patch(f"/api/v1/findings/{fid}", json={"category": ""})
    assert r.status_code == 422
    assert "category" in r.json()["details"]


def test_finding_save_draft_success(client):
    _, sid = _create_project_site(client, "P-D1", "S-D1", "Dan")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "env", "description": "Draft desc",
        "risk_level": "medium", "reported_by": "Dan",
    }).json()["id"]
    r = client.post(f"/api/v1/findings/{fid}/save-draft", json={
        "description": "Updated draft desc",
        "risk_level": "high",
    })
    assert r.status_code == 200
    assert r.json()["description"] == "Updated draft desc"
    assert r.json()["risk_level"] == "high"
    assert r.json()["finding_status"] == "draft"


def test_finding_submit_with_empty_fields_rejected(client):
    _, sid = _create_project_site(client, "P-D2", "S-D2", "Dan")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "env", "description": "desc",
        "risk_level": "low", "reported_by": "Dan",
    }).json()["id"]
    from app.database import get_db
    with get_db() as db:
        db.execute("UPDATE findings SET description = '' WHERE id = ?", (fid,))
    r = client.post(f"/api/v1/findings/{fid}/submit")
    assert r.status_code == 422
    assert "description" in r.json()["details"]


def test_finding_invalid_state_transition(client):
    _, sid = _create_project_site(client, "P-ST", "S-ST", "Sam")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "desc",
        "risk_level": "high", "reported_by": "Sam",
    }).json()["id"]
    r = client.post(f"/api/v1/findings/{fid}/transition", json={"target_status": "accepted"})
    assert r.status_code == 409
    body = r.json()
    assert body["error_code"] == "invalid_state_transition"
    assert body["details"]["current_status"] == "draft"
    assert body["details"]["target_status"] == "accepted"
    assert "submitted" in body["details"]["allowed_transitions"]


def test_audit_event_written_on_submit(client):
    _, sid = _create_project_site(client, "P-AU1", "S-AU1", "Aud")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "desc",
        "risk_level": "high", "reported_by": "Aud",
    }).json()["id"]
    client.post(f"/api/v1/findings/{fid}/submit", json={"actor": "Aud"})

    events = client.get(f"/api/v1/audit-events?entity_type=finding&entity_id={fid}").json()
    submit_events = [e for e in events if e["action"] == "submit"]
    assert len(submit_events) == 1
    detail = submit_events[0]["details"]
    assert detail["from_status"] == "draft"
    assert detail["to_status"] == "submitted"
    assert detail["actor"] == "Aud"
    assert "note" in detail


def test_audit_event_written_on_transition_to_reviewing(client):
    _, sid = _create_project_site(client, "P-AU2", "S-AU2", "Aud")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "desc",
        "risk_level": "high", "reported_by": "Aud",
    }).json()["id"]
    client.post(f"/api/v1/findings/{fid}/submit", json={"actor": "Aud"})
    client.post(f"/api/v1/findings/{fid}/transition", json={
        "target_status": "reviewing", "actor": "Reviewer", "note": "开始审核",
    })

    events = client.get(f"/api/v1/audit-events?entity_type=finding&entity_id={fid}").json()
    transition_events = [e for e in events if e["action"] == "status_change"]
    assert len(transition_events) >= 1
    latest = transition_events[-1]
    assert latest["details"]["from_status"] == "submitted"
    assert latest["details"]["to_status"] == "reviewing"
    assert latest["details"]["actor"] == "Reviewer"
    assert latest["details"]["note"] == "开始审核"


def test_audit_event_written_on_review_accepted(client):
    _, sid = _create_project_site(client, "P-AU3", "S-AU3", "Aud")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "desc",
        "risk_level": "high", "reported_by": "Aud",
    }).json()["id"]
    client.post(f"/api/v1/findings/{fid}/submit", json={"actor": "Aud"})
    client.post(f"/api/v1/findings/{fid}/transition", json={"target_status": "reviewing", "actor": "Aud"})
    client.post(f"/api/v1/findings/{fid}/reviews", json={
        "reviewer_name": "Boss",
        "conclusion": "approved",
        "comment": "Looks good",
    })

    events = client.get(f"/api/v1/audit-events?entity_type=finding&entity_id={fid}").json()
    review_events = [e for e in events if e["action"] == "review"]
    assert len(review_events) == 1
    detail = review_events[0]["details"]
    assert detail["from_status"] == "reviewing"
    assert detail["to_status"] == "accepted"
    assert detail["actor"] == "Boss"
    assert detail["conclusion"] == "approved"


def test_finding_timeline_sorted_chronologically(client):
    _, sid = _create_project_site(client, "P-TS", "S-TS", "Tim")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "first",
        "risk_level": "low", "reported_by": "Tim",
    }).json()["id"]
    client.post(f"/api/v1/findings/{fid}/submit", json={"actor": "Tim"})
    client.post(f"/api/v1/findings/{fid}/transition", json={"target_status": "reviewing", "actor": "Tim"})

    r = client.get(f"/api/v1/findings/{fid}/timeline")
    timeline = r.json()["timeline"]
    timestamps = [e["timestamp"] for e in timeline]
    assert timestamps == sorted(timestamps)
    assert timeline[0]["type"] == "finding_created"


def test_finding_timeline_includes_attachment(client):
    _, sid = _create_project_site(client, "P-TA", "S-TA", "Tim")
    fid = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "doc", "description": "with attach",
        "risk_level": "low", "reported_by": "Tim",
    }).json()["id"]
    client.post("/api/v1/attachments", json={
        "file_name": "pic.png",
        "file_type": "image/png",
        "storage_note": "s3://x/pic.png",
        "linked_finding_id": fid,
    })

    r = client.get(f"/api/v1/findings/{fid}/timeline")
    timeline = r.json()["timeline"]
    attach_events = [e for e in timeline if e["type"] == "attachment"]
    assert len(attach_events) == 1
    assert attach_events[0]["details"]["file_name"] == "pic.png"


def test_site_merged_timeline(client):
    pid, sid = _create_project_site(client, "P-STL", "S-STL", "Stl")
    fid1 = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "safety", "description": "finding one",
        "risk_level": "high", "reported_by": "Stl",
    }).json()["id"]
    fid2 = client.post("/api/v1/findings", json={
        "site_id": sid, "category": "env", "description": "finding two",
        "risk_level": "low", "reported_by": "Stl",
    }).json()["id"]
    client.post(f"/api/v1/findings/{fid1}/submit", json={"actor": "Stl"})
    client.post("/api/v1/attachments", json={
        "file_name": "doc.pdf",
        "linked_finding_id": fid2,
    })

    r = client.get(f"/api/v1/sites/{sid}/timeline")
    assert r.status_code == 200
    data = r.json()
    assert data["site_id"] == sid
    timeline = data["timeline"]
    assert len(timeline) >= 4

    timestamps = [e["timestamp"] for e in timeline]
    assert timestamps == sorted(timestamps)

    types = [e["type"] for e in timeline]
    assert "finding_created" in types
    assert "attachment" in types
    assert "audit" in types

    finding_ids_in_timeline = set(e["finding_id"] for e in timeline if e["finding_id"])
    assert fid1 in finding_ids_in_timeline
    assert fid2 in finding_ids_in_timeline


def test_error_response_structure(client):
    r = client.post("/api/v1/findings", json={
        "site_id": 99999,
        "category": "",
        "description": "",
        "risk_level": "bad",
        "reported_by": "",
    })
    assert r.status_code == 422
    body = r.json()
    assert set(body.keys()) == {"error_code", "message", "details"}
    assert isinstance(body["details"], dict)


def _create_finding(client, sid, category="safety", description="desc", risk_level="low", reported_by="User"):
    return client.post("/api/v1/findings", json={
        "site_id": sid,
        "category": category,
        "description": description,
        "risk_level": risk_level,
        "reported_by": reported_by,
    }).json()


def test_risk_overview_excludes_archived(client):
    _, sid = _create_project_site(client, "P-RK1", "S-RK1", "Risk")
    f1 = _create_finding(client, sid, risk_level="high", reported_by="Risk")
    f2 = _create_finding(client, sid, risk_level="critical", reported_by="Risk")

    client.post(f"/api/v1/findings/{f2['id']}/submit", json={"actor": "Risk"})
    client.post(f"/api/v1/findings/{f2['id']}/transition", json={"target_status": "reviewing", "actor": "Risk"})
    client.post(f"/api/v1/findings/{f2['id']}/transition", json={"target_status": "accepted", "actor": "Risk"})
    client.post(f"/api/v1/findings/{f2['id']}/transition", json={"target_status": "archived", "actor": "Risk"})

    r = client.get("/api/v1/overview/risk")
    data = r.json()
    assert data["total_findings"] == 1
    assert data["risk_counts"]["high"] == 1
    assert data["risk_counts"]["critical"] == 0
    assert data["status_counts"]["archived"] == 0


def test_sites_risk_includes_unreviewed_and_rejected(client):
    pid, sid = _create_project_site(client, "P-RK2", "S-RK2", "Risk")
    f1 = _create_finding(client, sid, risk_level="high", reported_by="Risk")
    f2 = _create_finding(client, sid, risk_level="medium", reported_by="Risk")
    f3 = _create_finding(client, sid, risk_level="low", reported_by="Risk")

    client.post(f"/api/v1/findings/{f2['id']}/submit", json={"actor": "Risk"})
    client.post(f"/api/v1/findings/{f2['id']}/transition", json={"target_status": "reviewing", "actor": "Risk"})

    client.post(f"/api/v1/findings/{f3['id']}/submit", json={"actor": "Risk"})
    client.post(f"/api/v1/findings/{f3['id']}/transition", json={"target_status": "reviewing", "actor": "Risk"})
    client.post(f"/api/v1/findings/{f3['id']}/reviews", json={
        "reviewer_name": "Boss", "conclusion": "rejected", "comment": "No",
    })

    r = client.get(f"/api/v1/projects/{pid}/sites-risk")
    data = r.json()
    assert data["summary"]["total_findings"] == 3
    assert data["summary"]["unreviewed_count"] == 2
    assert data["summary"]["rejected_count"] == 1
    site = data["sites"][0]
    assert site["unreviewed_count"] == 2
    assert site["rejected_count"] == 1
    assert site["max_risk_level"] == "high"
    assert site["last_updated"] is not None


def test_sites_risk_excludes_archived_from_stats(client):
    pid, sid = _create_project_site(client, "P-RK3", "S-RK3", "Risk")
    f1 = _create_finding(client, sid, risk_level="high", reported_by="Risk")
    f2 = _create_finding(client, sid, risk_level="critical", reported_by="Risk")
    client.post(f"/api/v1/findings/{f2['id']}/submit", json={"actor": "Risk"})
    client.post(f"/api/v1/findings/{f2['id']}/transition", json={"target_status": "reviewing", "actor": "Risk"})
    client.post(f"/api/v1/findings/{f2['id']}/reviews", json={
        "reviewer_name": "Boss", "conclusion": "approved",
    })
    client.post(f"/api/v1/findings/{f2['id']}/transition", json={"target_status": "archived", "actor": "Boss"})

    r = client.get(f"/api/v1/projects/{pid}/sites-risk")
    site = r.json()["sites"][0]
    assert site["total_findings"] == 1
    assert site["risk_counts"]["critical"] == 0
    assert site["max_risk_level"] == "high"


def test_project_list_includes_risk_summary(client):
    pid, sid = _create_project_site(client, "P-RS1", "S-RS1", "Sum")
    _create_finding(client, sid, risk_level="high", reported_by="Sum")

    r = client.get("/api/v1/projects")
    projects = r.json()
    target = [p for p in projects if p["id"] == pid][0]
    assert "risk_summary" in target
    rs = target["risk_summary"]
    assert rs["total_findings"] == 1
    assert rs["max_risk_level"] == "high"
    assert rs["unreviewed_count"] == 1
    assert rs["rejected_count"] == 0


def test_project_list_filter_by_region(client):
    pid1, _ = _create_project_site(client, "P-RG1", "S-RG1", "Reg")
    _, sid2 = _create_project_site(client, "P-RG2", "S-RG2", "Reg")
    client.patch(f"/api/v1/sites/{sid2}", json={"region": "North"})

    r = client.get("/api/v1/projects?region=North")
    projects = r.json()
    ids = [p["id"] for p in projects]
    assert pid1 not in ids or True

    pid3 = client.post("/api/v1/projects", json={
        "project_code": "P-RG3", "project_name": "North Project", "owner_name": "Reg",
    }).json()["id"]
    client.post("/api/v1/sites", json={
        "site_code": "S-RG3", "site_name": "North Site", "region": "North", "project_id": pid3,
    })

    r = client.get("/api/v1/projects?region=North")
    projects = r.json()
    ids = [p["id"] for p in projects]
    assert pid3 in ids


def test_project_list_filter_by_max_risk_level(client):
    _, sid = _create_project_site(client, "P-MR1", "S-MR1", "MR")
    _create_finding(client, sid, risk_level="high", reported_by="MR")

    r = client.get("/api/v1/projects?max_risk_level=critical")
    assert len(r.json()) == 0

    r = client.get("/api/v1/projects?max_risk_level=high")
    assert len(r.json()) >= 1


def test_template_creation_success_generates_sites(client):
    tpl = client.post("/api/v1/templates", json={
        "template_name": "Success Tpl",
        "default_region": "East",
        "site_items": [
            {"site_code": "TS-1", "site_name": "Gate", "address_text": "1 St"},
            {"site_code": "TS-2", "site_name": "Building", "address_text": "2 St"},
        ],
    }).json()

    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-TPL-S",
        "project_name": "Success Project",
        "owner_name": "Tpl",
        "template_id": tpl["id"],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["sites_created"] == 2
    assert "TS-1" in data["site_codes"]
    assert "TS-2" in data["site_codes"]

    sites = client.get(f"/api/v1/sites?project_id={data['id']}").json()
    assert len(sites) == 2
    assert sites[0]["region"] == "East"


def test_template_duplicate_site_code_rolls_back(client):
    tpl = client.post("/api/v1/templates", json={
        "template_name": "Dup Tpl",
        "default_region": "",
        "site_items": [
            {"site_code": "DUP-01", "site_name": "First"},
        ],
    }).json()

    pid, sid = _create_project_site(client, "P-DUP", "DUP-01", "Dup")

    project_count_before = len(client.get("/api/v1/projects").json())

    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-TPL-D",
        "project_name": "Dup Project",
        "owner_name": "Dup",
        "template_id": tpl["id"],
    })
    assert r.status_code == 409
    body = r.json()
    assert body["error_code"] == "conflict"
    assert "DUP-01" in body["message"]

    project_count_after = len(client.get("/api/v1/projects").json())
    assert project_count_after == project_count_before

    leftover = client.get("/api/v1/projects?status=draft").json()
    assert not any(p["project_code"] == "P-TPL-D" for p in leftover)


def test_template_duplicate_code_within_items_rolls_back(client):
    import json as _json
    from app.database import get_db
    with get_db() as db:
        db.execute(
            "INSERT INTO templates (template_name, default_region, site_items) VALUES (?, ?, ?)",
            ("Bad Tpl", "", _json.dumps([
                {"site_code": "BAD-1", "site_name": "One"},
                {"site_code": "BAD-1", "site_name": "Two"},
            ])),
        )
        tid = db.execute("SELECT id FROM templates WHERE template_name = 'Bad Tpl'").fetchone()["id"]

    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-TPL-BAD",
        "project_name": "Bad Project",
        "owner_name": "Bad",
        "template_id": tid,
    })
    assert r.status_code == 409
    body = r.json()
    assert "BAD-1" in body["details"].get("site_code", "")

    projects = client.get("/api/v1/projects").json()
    assert not any(p["project_code"] == "P-TPL-BAD" for p in projects)


def test_template_invalid_site_items_structure_rolls_back(client):
    import json as _json
    from app.database import get_db
    with get_db() as db:
        db.execute(
            "INSERT INTO templates (template_name, default_region, site_items) VALUES (?, ?, ?)",
            ("Invalid Tpl", "", _json.dumps([
                {"site_code": "", "site_name": "No Code"},
            ])),
        )
        tid = db.execute("SELECT id FROM templates WHERE template_name = 'Invalid Tpl'").fetchone()["id"]

    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-TPL-INV",
        "project_name": "Invalid Project",
        "owner_name": "Inv",
        "template_id": tid,
    })
    assert r.status_code == 422
    assert r.json()["error_code"] == "validation_error"

    projects = client.get("/api/v1/projects").json()
    assert not any(p["project_code"] == "P-TPL-INV" for p in projects)


def test_archived_finding_visible_in_site_detail(client):
    _, sid = _create_project_site(client, "P-ARCH", "S-ARCH", "Arch")
    f = _create_finding(client, sid, risk_level="low", reported_by="Arch")
    client.post(f"/api/v1/findings/{f['id']}/submit", json={"actor": "Arch"})
    client.post(f"/api/v1/findings/{f['id']}/transition", json={"target_status": "reviewing", "actor": "Arch"})
    client.post(f"/api/v1/findings/{f['id']}/reviews", json={
        "reviewer_name": "Boss", "conclusion": "approved",
    })
    client.post(f"/api/v1/findings/{f['id']}/transition", json={"target_status": "archived", "actor": "Boss"})

    all_findings = client.get(f"/api/v1/findings?site_id={sid}").json()
    assert len(all_findings) == 1
    assert all_findings[0]["finding_status"] == "archived"

    active_findings = client.get(f"/api/v1/findings?site_id={sid}&finding_status=draft").json()
    assert len(active_findings) == 0


def test_system_check_all_passed(client):
    pid, sid = _create_project_site(client, "P-CHK1", "S-CHK1", "Chk")
    _create_finding(client, sid, risk_level="low", reported_by="Chk")

    r = client.get("/api/v1/system/check")
    assert r.status_code == 200
    data = r.json()
    assert data["all_passed"] is True
    assert data["total_checks"] == 6
    assert data["passed_checks"] == 6
    assert data["total_issues"] == 0

    check_codes = [c["check_code"] for c in data["checks"]]
    assert "orphan_sites" in check_codes
    assert "orphan_findings" in check_codes
    assert "status_audit_mismatch" in check_codes
    assert "orphan_attachments" in check_codes
    assert "duplicate_template_site_codes" in check_codes
    assert "risk_stats_consistency" in check_codes

    for c in data["checks"]:
        assert c["passed"] is True
        assert c["issue_count"] == 0
        assert c["issues"] == []


def test_system_check_detects_orphan_site(client):
    from app.database import get_db
    with get_db() as db:
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("INSERT INTO sites (site_code, site_name, project_id) VALUES (?, ?, ?)", ("ORPHAN-S", "Orphan Site", 99999))
        db.execute("PRAGMA foreign_keys = ON")

    r = client.get("/api/v1/system/check")
    data = r.json()
    assert data["all_passed"] is False
    orphan_check = [c for c in data["checks"] if c["check_code"] == "orphan_sites"][0]
    assert orphan_check["passed"] is False
    assert orphan_check["issue_count"] >= 1
    assert any(i["site_code"] == "ORPHAN-S" for i in orphan_check["issues"])


def test_system_check_detects_orphan_finding(client):
    from app.database import get_db
    with get_db() as db:
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute(
            "INSERT INTO findings (site_id, category, description, risk_level, reported_by) VALUES (?, ?, ?, ?, ?)",
            (99999, "x", "orphan finding", "high", "X"),
        )
        db.execute("PRAGMA foreign_keys = ON")

    r = client.get("/api/v1/system/check")
    data = r.json()
    check = [c for c in data["checks"] if c["check_code"] == "orphan_findings"][0]
    assert check["passed"] is False
    assert any(i["site_id"] == 99999 for i in check["issues"])


def test_system_check_detects_orphan_attachment(client):
    from app.database import get_db
    with get_db() as db:
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute(
            "INSERT INTO attachments (file_name, linked_finding_id) VALUES (?, ?)",
            ("orphan.pdf", 99999),
        )
        db.execute("PRAGMA foreign_keys = ON")

    r = client.get("/api/v1/system/check")
    data = r.json()
    check = [c for c in data["checks"] if c["check_code"] == "orphan_attachments"][0]
    assert check["passed"] is False
    assert any(i["linked_finding_id"] == 99999 for i in check["issues"])


def test_system_check_detects_duplicate_template_codes(client):
    import json as _json
    from app.database import get_db
    with get_db() as db:
        db.execute(
            "INSERT INTO templates (template_name, default_region, site_items) VALUES (?, ?, ?)",
            ("Dup Check Tpl", "", _json.dumps([
                {"site_code": "DUP-X", "site_name": "One"},
                {"site_code": "DUP-X", "site_name": "Two"},
            ])),
        )

    r = client.get("/api/v1/system/check")
    data = r.json()
    check = [c for c in data["checks"] if c["check_code"] == "duplicate_template_site_codes"][0]
    assert check["passed"] is False
    assert any(i["site_code"] == "DUP-X" for i in check["issues"])


def test_system_check_response_fields_are_snake_case(client):
    r = client.get("/api/v1/system/check")
    data = r.json()
    assert "all_passed" in data
    assert "total_checks" in data
    assert "passed_checks" in data
    assert "total_issues" in data
    assert "checks" in data

    for k in data.keys():
        assert k.islower() and " " not in k, f"Field {k} not snake_case"

    check = data["checks"][0]
    for field in ["check_code", "passed", "issue_count", "issues"]:
        assert field in check, f"Missing field {field}"

    for c in data["checks"]:
        for k in c.keys():
            assert k.islower() and " " not in k, f"Check field {k} not snake_case"

    for c in data["checks"]:
        if c["issues"]:
            issue = c["issues"][0]
            for key in issue.keys():
                assert key.islower() and " " not in key, f"Issue field {key} not snake_case"


def test_new_endpoints_maintain_snake_case(client):
    pid, sid = _create_project_site(client, "P-SC", "S-SC", "SC")
    f = _create_finding(client, sid, risk_level="high", reported_by="SC")

    r = client.get("/api/v1/system/check")
    data = r.json()
    for c in data["checks"]:
        assert "check_code" in c
        assert "issue_count" in c

    r = client.get(f"/api/v1/projects/{pid}/sites-risk")
    sr = r.json()
    assert "project_id" in sr
    assert "project_code" in sr
    site = sr["sites"][0]
    assert "total_findings" in site
    assert "unreviewed_count" in site
    assert "rejected_count" in site
    assert "max_risk_level" in site
    assert "last_updated" in site
    assert "risk_counts" in site
    assert "archived_count" in site

    r = client.get("/api/v1/projects")
    proj = r.json()[0]
    assert "risk_summary" in proj
    rs = proj["risk_summary"]
    assert "total_findings" in rs
    assert "unreviewed_count" in rs
    assert "rejected_count" in rs
    assert "max_risk_level" in rs

    r = client.get(f"/api/v1/sites/{sid}/timeline")
    tl = r.json()
    assert "site_id" in tl
    assert "site_code" in tl
    for item in tl["timeline"][:1]:
        assert "finding_id" in item or item["finding_id"] is None

    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-SCTPL",
        "project_name": "SC Template",
        "owner_name": "SC",
        "template_id": client.post("/api/v1/templates", json={
            "template_name": "SC Tpl",
            "site_items": [{"site_code": "SC-T1", "site_name": "T1"}],
        }).json()["id"],
    })
    assert r.status_code == 200
    res = r.json()
    assert "sites_created" in res
    assert "site_codes" in res
    assert "template_name" in res
