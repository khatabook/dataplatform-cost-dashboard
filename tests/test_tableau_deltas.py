from app.collectors.tableau import daily_view_deltas


def test_daily_view_deltas_are_non_negative():
    yesterday = [{"object_id": "v1", "view_count": 100}, {"object_id": "v2", "view_count": 50}]
    today = [{"object_id": "v1", "view_count": 110}, {"object_id": "v2", "view_count": 40}]
    deltas = {r["object_id"]: r["view_count"] for r in daily_view_deltas(today, yesterday)}
    assert deltas["v1"] == 10
    assert deltas["v2"] == 0
