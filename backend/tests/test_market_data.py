from app.data.market_data import closest_price_before, pct_change


def test_pct_change_basic():
    assert pct_change(110, 100) == 10.0
    assert pct_change(90, 100) == -10.0
    assert pct_change(100, 0) is None
    assert pct_change(100, None) is None


def test_closest_price_before():
    series = [(1000, 10.0), (2000, 20.0), (3000, 30.0)]
    assert closest_price_before(series, 2500) == 20.0
    assert closest_price_before(series, 1000) == 10.0
    assert closest_price_before(series, 500) is None
    assert closest_price_before(series, 3000) == 30.0
