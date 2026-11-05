from datetime import date
from pathlib import Path
import json

from app.collectors.kubecost import parse_allocation


def test_parse_allocation_filters_and_aggregates():
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "kubecost_allocation.json").read_text()
    )
    rows = parse_allocation(
        payload,
        date(2026, 11, 1),
        ["airflow", "rudderstack", "redash"],
    )
    by_service = {r["service"]: r for r in rows}
    assert by_service["airflow"]["total_usd"] == 24.2
    assert by_service["rudderstack"]["cpu_usd"] == 40.0
    assert by_service["redash"]["network_usd"] == 0.2
    assert set(by_service) == {"airflow", "rudderstack", "redash"}
