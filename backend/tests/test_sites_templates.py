def _create_project(client, code="P-1"):
    return client.post("/api/v1/projects", json={
        "project_code": code, "project_name": "Project", "owner_name": "Owner",
    }).json()


def _create_template(client):
    return client.post("/api/v1/templates", json={
        "template_name": "Retail Sites",
        "default_region": "East",
        "site_items": [
            {"site_code": "S-001", "site_name": "Downtown", "address_text": "1 St", "region": "East"},
            {"site_code": "S-002", "site_name": "Mall", "address_text": "2 Ave"},
        ],
    }).json()


def test_template_creation_and_list(client):
    tpl = _create_template(client)
    assert tpl["site_items"][0]["site_code"] == "S-001"

    r = client.get("/api/v1/templates")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_create_project_from_template_batch_sites(client):
    tpl = _create_template(client)
    r = client.post("/api/v1/projects/from-template", json={
        "project_code": "P-T",
        "project_name": "Templated",
        "owner_name": "Bob",
        "template_id": tpl["id"],
    })
    assert r.status_code == 201
    project = r.json()
    assert project["project_id"]
    assert project["total_sites"] == 2
    pid = project["project_id"]

    sites = client.get("/api/v1/sites", params={"project_id": pid}).json()
    assert len(sites) == 2
    assert sites[1]["region"] == "East"


def test_site_crud_and_region_filter(client):
    p = _create_project(client)
    s = client.post("/api/v1/sites", json={
        "project_id": p["id"], "site_code": "A1", "site_name": "Site A",
        "address_text": "addr", "region": "North",
    }).json()

    r = client.patch(f"/api/v1/sites/{s['id']}", json={"region": "South"})
    assert r.status_code == 200
    assert r.json()["region"] == "South"

    r = client.get("/api/v1/sites", params={"project_id": p["id"], "region": "South"})
    assert len(r.json()) == 1

    r = client.delete(f"/api/v1/sites/{s['id']}")
    assert r.status_code == 204
    r = client.get(f"/api/v1/sites/{s['id']}")
    assert r.status_code == 404
