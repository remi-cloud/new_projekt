from app.ai.academy import academy_payload


def test_academy_is_defensive_education_without_secrets():
    data = academy_payload()
    blob = str(data).lower()
    assert data["parts"][0]["id"] == "ai"
    assert data["parts"][1]["id"] == "security"
    assert "ic3.gov" in blob
    assert "incydent.cert.pl" in blob
    assert "nie stanowi porady" in data["disclaimer"].lower() or "nie stanowi porady" in blob
    assert "api_key" not in blob
    assert "sk-" not in blob
    # Defense copy, not an attack recipe.
    for banned in ("reverse shell", "metasploit", "sql injection"):
        assert banned not in blob
