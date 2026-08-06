from app.ai.self_learn import _parse_lessons


def test_parse_lessons_json():
    raw = '{"lessons":[{"topic":"fed","lesson":"Watch CPI surprises before pricing cuts.","confidence":0.8}]}'
    out = _parse_lessons(raw)
    assert len(out) == 1
    assert out[0]["topic"] == "fed"
    assert "CPI" in out[0]["lesson"]


def test_parse_lessons_fenced():
    raw = '```json\n{"lessons":[{"topic":"btc","lesson":"Halving cycle still frames risk appetite.","confidence":0.7}]}\n```'
    out = _parse_lessons(raw)
    assert len(out) == 1


def test_parse_lessons_skips_short():
    assert _parse_lessons('{"lessons":[{"topic":"x","lesson":"too short","confidence":1}]}') == []
