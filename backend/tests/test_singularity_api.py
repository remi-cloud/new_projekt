"""Singularity API smoke (no full pipeline / no network)."""


def test_singularity_status_shape(client):
    r = client.get("/api/singularity/status")
    assert r.status_code == 200
    data = r.json()
    assert data.get("module") == "Singularity"
    assert "long_scouts" in data
    assert "short_scouts" in data
    assert isinstance(data["long_scouts"], list)
    assert isinstance(data["short_scouts"], list)
    assert "pipeline" in data


def test_agents_status_alias(client):
    r = client.get("/api/agents/status")
    assert r.status_code == 200
    assert r.json().get("brand") == "Kar Digital"
