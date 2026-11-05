from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable

import httpx
from sqlalchemy.orm import Session

from app.collectors.upsert import upsert_rows
from app.config import Settings
from app.db.models import BiActivityDaily


class TableauCollector:
    name = "tableau"

    def __init__(
        self,
        snapshot_fn: Callable[..., list[dict[str, Any]]] | None = None,
    ) -> None:
        self._snapshot_fn = snapshot_fn or fetch_tableau_view_counts

    def configured(self, settings: Settings) -> bool:
        return settings.tableau_configured()

    def collect(self, session: Session, settings: Settings, day: date) -> None:
        """Store cumulative view counts; API layer diffs day-over-day for charts."""
        rows = self._snapshot_fn(settings)
        upsert_rows(
            session,
            BiActivityDaily,
            [
                {
                    "tool": "tableau",
                    "day": day,
                    "user_name": str(row.get("user_name") or "site"),
                    "object_id": str(row.get("object_id") or ""),
                    "object_name": row.get("object_name"),
                    "view_count": int(row.get("view_count") or 0),
                }
                for row in rows
                if row.get("object_id")
            ],
            conflict_cols=["tool", "day", "user_name", "object_id"],
            update_cols=["object_name", "view_count"],
        )


def fetch_tableau_view_counts(settings: Settings) -> list[dict[str, Any]]:
    base = settings.tableau_server_url.rstrip("/")
    site = settings.tableau_site
    with httpx.Client(timeout=60.0) as client:
        signin = client.post(
            f"{base}/api/3.21/auth/signin",
            json={
                "credentials": {
                    "personalAccessTokenName": settings.tableau_pat_name,
                    "personalAccessTokenSecret": settings.tableau_pat_secret,
                    "site": {"contentUrl": site},
                }
            },
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        signin.raise_for_status()
        creds = signin.json()["credentials"]
        token = creds["token"]
        site_id = creds["site"]["id"]
        headers = {"X-Tableau-Auth": token, "Accept": "application/json"}

        views_resp = client.get(
            f"{base}/api/3.21/sites/{site_id}/views",
            params={"pageSize": 1000},
            headers=headers,
        )
        views_resp.raise_for_status()
        views = (views_resp.json().get("views") or {}).get("view") or []

        rows: list[dict[str, Any]] = []
        for view in views:
            view_id = view.get("id")
            name = view.get("name")
            usage = (view.get("usage") or {}).get("totalViewCount")
            if usage is None:
                # Some Tableau versions expose usage via a separate endpoint.
                usage_resp = client.get(
                    f"{base}/api/3.21/sites/{site_id}/views/{view_id}",
                    headers=headers,
                )
                if usage_resp.status_code == 200:
                    usage = (
                        (usage_resp.json().get("view") or {})
                        .get("usage", {})
                        .get("totalViewCount", 0)
                    )
                else:
                    usage = 0
            rows.append(
                {
                    "user_name": "site",
                    "object_id": view_id,
                    "object_name": name,
                    "view_count": int(usage or 0),
                }
            )

        client.post(f"{base}/api/3.21/auth/signout", headers=headers)
        return rows


def daily_view_deltas(
    today_rows: list[dict[str, Any]],
    yesterday_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Helper for tests / API: convert cumulative counters to day deltas."""
    prev = {r["object_id"]: int(r.get("view_count") or 0) for r in yesterday_rows}
    out = []
    for row in today_rows:
        oid = row["object_id"]
        delta = max(0, int(row.get("view_count") or 0) - prev.get(oid, 0))
        out.append({**row, "view_count": delta})
    return out
