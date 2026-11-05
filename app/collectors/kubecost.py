from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.collectors.upsert import upsert_rows
from app.config import Settings
from app.db.models import InfraCostDaily


class KubecostCollector:
    name = "kubecost"

    def configured(self, settings: Settings) -> bool:
        return bool(settings.kubecost_base_url) and bool(settings.kubecost_service_list())

    def collect(self, session: Session, settings: Settings, day: date) -> None:
        rows = fetch_allocation(settings, day)
        upsert_rows(
            session,
            InfraCostDaily,
            rows,
            conflict_cols=["service", "day"],
            update_cols=["cpu_usd", "ram_usd", "pv_usd", "network_usd", "total_usd"],
        )


def fetch_allocation(settings: Settings, day: date) -> list[dict[str, Any]]:
    """Call Kubecost allocation API and aggregate by infra-service label."""
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    params = {
        "window": f"{start.isoformat()},{end.isoformat()}",
        "aggregate": "label:infra-service",
        "accumulate": "true",
    }
    url = settings.kubecost_base_url.rstrip("/") + "/model/allocation"
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    return parse_allocation(payload, day, settings.kubecost_service_list())


def parse_allocation(
    payload: dict[str, Any],
    day: date,
    services: list[str],
) -> list[dict[str, Any]]:
    data = payload.get("data") or []
    buckets: dict[str, dict[str, float]] = {
        s: {"cpu_usd": 0.0, "ram_usd": 0.0, "pv_usd": 0.0, "network_usd": 0.0, "total_usd": 0.0}
        for s in services
    }
    wanted = {s.lower(): s for s in services}

    for window in data:
        if not isinstance(window, dict):
            continue
        for key, item in window.items():
            if key == "__idle__" or not isinstance(item, dict):
                continue
            service_key = key.lower()
            # Kubecost may return "infra-service=airflow" or just "airflow"
            if "=" in service_key:
                service_key = service_key.split("=", 1)[-1]
            if service_key not in wanted:
                continue
            name = wanted[service_key]
            cpu = float(item.get("cpuCost") or 0.0)
            ram = float(item.get("ramCost") or 0.0)
            pv = float(item.get("pvCost") or 0.0)
            network = float(item.get("networkCost") or 0.0)
            total = float(item.get("totalCost") or (cpu + ram + pv + network))
            buckets[name]["cpu_usd"] += cpu
            buckets[name]["ram_usd"] += ram
            buckets[name]["pv_usd"] += pv
            buckets[name]["network_usd"] += network
            buckets[name]["total_usd"] += total

    return [
        {
            "service": service,
            "day": day,
            "cpu_usd": values["cpu_usd"],
            "ram_usd": values["ram_usd"],
            "pv_usd": values["pv_usd"],
            "network_usd": values["network_usd"],
            "total_usd": values["total_usd"],
        }
        for service, values in buckets.items()
    ]
