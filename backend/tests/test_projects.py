def test_create_and_list_project(client):
    resp = client.post("/api/v1/projects", json={
        "project_code": "P-001",
        "project_name": "North Field Survey",
        "owner_name": "Alice",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["project_code"] == "P-001"
    assert data["status"] == "draft"

    resp = client.get("/api/v1/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_duplicate_project_code_conflict(client):
    client.post("/api/v1/projects", json={
        "project_code": "P-DUP", "project_name": "A", "owner_name": "A",
    })
    resp = client.post("/api/v1/projects", json={
        "project_code": "P-DUP", "project_name": "B", "owner_name": "B",
    })
    assert resp.status_code == 409
    body = resp.json()
    assert body["error_code"] == "conflict"
    assert "message" in body and "details" in body


def test_project_status_transition(client):
    pid = client.post("/api/v1/projects", json={
        "project_code": "P-S", "project_name": "S", "owner_name": "O",
    }).json()["id"]

    r = client.patch(f"/api/v1/projects/{pid}/status", json={"status": "submitted"})
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"

    r = client.patch(f"/api/v1/projects/{pid}/status", json={"status": "draft"})
    assert r.status_code == 422


def test_not_found_shape(client):
    r = client.get("/api/v1/projects/9999")
    assert r.status_code == 404
    body = r.json()
    assert set(body.keys()) == {"error_code", "message", "details"}
