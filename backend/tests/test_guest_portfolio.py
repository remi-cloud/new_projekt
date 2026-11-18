"""Guests get market tools. The paper book stays behind the desk cookie."""

from fastapi.testclient import TestClient

SECRET = "424242"
COIN = "SECRET-COIN"


def test_guest_chat_hides_the_paper_book(client: TestClient, monkeypatch):
    async def book():
        return {"summary": {"total_equity_pln": int(SECRET)}, "positions": [{"symbol": COIN}]}

    monkeypatch.setattr("app.paper.portfolio_memory.get_agent_portfolio_context", book)
    client.cookies.clear()
    response = client.post(
        "/api/ai/chat",
        json={"message": "Pokaż mój portfel paper i gotówkę"},
        headers={"X-Desk-Token": ""},
    )
    assert response.status_code == 200
    assert SECRET not in response.text
    assert COIN not in response.text
    assert "get_paper_portfolio" not in response.json().get("tools_used", [])


def test_desk_chat_can_see_the_paper_book(client: TestClient, monkeypatch):
    async def book():
        return {"summary": {"total_equity_pln": int(SECRET), "equity": int(SECRET)}, "positions": [{"symbol": COIN}]}

    monkeypatch.setattr("app.paper.portfolio_memory.get_agent_portfolio_context", book)
    client.cookies.clear()
    response = client.post(
        "/api/ai/chat",
        json={"message": "Pokaż mój portfel paper i gotówkę"},
        headers={"X-Desk-Token": "pytest-desk"},
    )
    assert response.status_code == 200
    body = response.text
    assert SECRET in body or COIN in body
    assert "get_paper_portfolio" in response.json().get("tools_used", [])
