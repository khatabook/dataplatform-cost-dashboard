from __future__ import annotations

from datetime import date
from typing import Any, Callable

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.collectors.upsert import upsert_rows
from app.config import Settings
from app.db.models import BiActivityDaily

# Redash events table: action='view' for dashboard/query views.
REDASH_EVENTS_SQL = """
SELECT
    COALESCE(u.email, u.name, CAST(e.user_id AS TEXT), 'unknown') AS user_name,
    COALESCE(CAST(e.object_id AS TEXT), '0') AS object_id,
    COALESCE(d.name, CONCAT('object-', CAST(e.object_id AS TEXT))) AS object_name,
    COUNT(*) AS view_count
FROM events e
LEFT JOIN users u ON u.id = e.user_id
LEFT JOIN dashboards d ON d.id = e.object_id AND e.object_type = 'dashboard'
WHERE e.action = 'view'
  AND e.created_at::date = :day
GROUP BY 1, 2, 3
"""


class RedashCollector:
    name = "redash"

    def __init__(self, query_fn: Callable[..., list[dict[str, Any]]] | None = None) -> None:
        self._query_fn = query_fn or query_redash_events

    def configured(self, settings: Settings) -> bool:
        return settings.redash_configured()

    def collect(self, session: Session, settings: Settings, day: date) -> None:
        rows = self._query_fn(settings, day)
        upsert_rows(
            session,
            BiActivityDaily,
            [
                {
                    "tool": "redash",
                    "day": day,
                    "user_name": str(row.get("user_name") or "unknown"),
                    "object_id": str(row.get("object_id") or "0"),
                    "object_name": row.get("object_name"),
                    "view_count": int(row.get("view_count") or 0),
                }
                for row in rows
            ],
            conflict_cols=["tool", "day", "user_name", "object_id"],
            update_cols=["object_name", "view_count"],
        )


def query_redash_events(settings: Settings, day: date) -> list[dict[str, Any]]:
    engine = create_engine(settings.redash_database_url)
    with engine.connect() as conn:
        result = conn.execute(text(REDASH_EVENTS_SQL), {"day": day})
        return [dict(row._mapping) for row in result]
