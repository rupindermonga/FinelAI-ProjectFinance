"""Tests for the /api/admin/health endpoint."""


def test_health_endpoint_requires_auth(client):
    r = client.get("/api/admin/health")
    assert r.status_code == 401


def test_health_returns_all_sections(auth_client):
    r = auth_client.get("/api/admin/health")
    assert r.status_code == 200
    d = r.json()
    assert "worker" in d
    assert "pipeline" in d
    assert "gemini" in d
    assert "db" in d


def test_health_worker_section_shape(auth_client):
    d = auth_client.get("/api/admin/health").json()
    w = d["worker"]
    assert "alive" in w
    assert "last_heartbeat_secs_ago" in w
    assert "queue_depth" in w
    assert "processed_session" in w


def test_health_pipeline_section_shape(auth_client):
    d = auth_client.get("/api/admin/health").json()
    p = d["pipeline"]
    for key in ("total", "processed", "pending", "errors", "stuck", "error_rate_pct_recent50"):
        assert key in p, f"Missing pipeline key: {key}"


def test_health_gemini_section_shape(auth_client):
    d = auth_client.get("/api/admin/health").json()
    g = d["gemini"]
    assert "keys_total" in g
    assert "keys_available" in g
    assert "keys_blacklisted" in g
    assert "paid_key_configured" in g
    assert g["keys_total"] >= 0


def test_health_db_connected(auth_client):
    d = auth_client.get("/api/admin/health").json()
    assert d["db"]["connected"] is True


def test_health_pipeline_totals_consistent(auth_client):
    """processed + pending + errors should not exceed total."""
    d = auth_client.get("/api/admin/health").json()
    p = d["pipeline"]
    assert p["processed"] + p["pending"] + p["errors"] <= p["total"] + 5  # +5 tolerance for race
