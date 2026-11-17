"""Public reads the desk UI calls must answer. Writes stay behind the token."""

from fastapi.testclient import TestClient

READS = (
    "/api/health",
    "/api/dashboard",
    "/api/desk/status",
    "/api/notifications/status",
    "/api/paper/portfolio",
    "/api/markets/chart-presets",
    "/api/markets/quote/BTC-USD",
    "/api/news/macro?limit=5",
    "/api/social/status",
    "/api/social/published",
    "/api/ai/status",
    "/api/ai/academy",
    "/api/coordinator/health",
    "/api/roi/assets",
    "/api/cycles/seasonality-health",
    "/api/cycles/global-book?status=all",
    "/api/cycles/session-clock",
    "/api/embed/cycle",
    "/api/public/live",
    "/api/growth/packages",
    "/api/backup/status",
    "/api/pearl/status",
    "/api/fomo/status",
    "/api/axiom/status",
    "/api/execution/status",
    "/api/telemetry/agent-vs-sp500?range=30d",
    "/api/super-opportunities?min_score=0",
    "/api/singularity",
    "/api/launch/status",
    "/api/launch/candidates?tier=seed",
)


def test_desk_reads_answer(client: TestClient):
    for path in READS:
        response = client.get(path)
        if path == "/api/dashboard" and response.status_code == 503:
            assert "skan" in response.text.lower() or "cykl" in response.text.lower()
            continue
        assert response.status_code < 400, f"{path} {response.status_code} {response.text[:180]}"


def test_ai_security_pages_are_public(client: TestClient):
    academy = client.get("/api/ai/academy")
    assert academy.status_code == 200
    body = academy.json()
    assert body["title"] == "AI i hacking"
    part_ids = {part["id"] for part in body["parts"]}
    assert "ai" in part_ids
    assert "security" in part_ids
    assert "obron" in body["disclaimer"].lower()
