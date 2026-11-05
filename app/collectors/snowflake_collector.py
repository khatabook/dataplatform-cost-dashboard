from __future__ import annotations

from datetime import date
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.collectors.upsert import upsert_rows
from app.config import Settings
from app.db.models import (
    SnowflakeCortexDaily,
    SnowflakeQuerySample,
    SnowflakeTeamUsageDaily,
)

TEAM_USAGE_SQL = """
SELECT
    w.start_time::date AS day,
    COALESCE(m.team, '(unmapped)') AS team,
    w.warehouse_name AS warehouse,
    SUM(w.credits_used) AS credits
FROM snowflake.account_usage.warehouse_metering_history w
LEFT JOIN analytics.public.warehouse_team_mapping m
    ON UPPER(w.warehouse_name) = UPPER(m.warehouse_name)
WHERE w.start_time::date = %(day)s
GROUP BY 1, 2, 3
"""

EXPENSIVE_QUERIES_SQL = """
SELECT
    q.query_id,
    q.user_name,
    q.query_tag AS job_tag,
    q.warehouse_name AS warehouse,
    COALESCE(q.total_elapsed_time, 0) / 1000.0 AS seconds,
    COALESCE(a.credits_attributed_compute, 0) AS credits,
    LEFT(COALESCE(q.query_text, ''), 500) AS query_text
FROM snowflake.account_usage.query_history q
LEFT JOIN snowflake.account_usage.query_attribution_history a
    ON q.query_id = a.query_id
WHERE q.start_time::date = %(day)s
  AND q.end_time IS NOT NULL
ORDER BY credits DESC NULLS LAST
LIMIT %(limit)s
"""

LONG_RUNNING_SQL = """
SELECT
    query_id,
    user_name,
    query_tag AS job_tag,
    warehouse_name AS warehouse,
    COALESCE(total_elapsed_time, 0) / 1000.0 AS seconds,
    0.0 AS credits,
    LEFT(COALESCE(query_text, ''), 500) AS query_text
FROM snowflake.account_usage.query_history
WHERE start_time::date = %(day)s
  AND end_time IS NOT NULL
ORDER BY total_elapsed_time DESC NULLS LAST
LIMIT %(limit)s
"""

CORTEX_SQL = """
SELECT
    usage_time::date AS day,
    user_name,
    SUM(token_credits) AS token_credits
FROM snowflake.account_usage.cortex_code_snowsight_usage_history
WHERE usage_time::date = %(day)s
GROUP BY 1, 2
"""


class SnowflakeCollector:
    name = "snowflake"

    def __init__(self, query_fn: Callable[..., list[dict[str, Any]]] | None = None) -> None:
        self._query_fn = query_fn or run_snowflake_query

    def configured(self, settings: Settings) -> bool:
        return settings.snowflake_configured()

    def collect(self, session: Session, settings: Settings, day: date) -> None:
        team_rows = self._query_fn(settings, TEAM_USAGE_SQL, {"day": day})
        upsert_rows(
            session,
            SnowflakeTeamUsageDaily,
            [
                {
                    "day": row["DAY"] if "DAY" in row else row["day"],
                    "team": str(row.get("TEAM") or row.get("team") or "(unmapped)"),
                    "warehouse": str(row.get("WAREHOUSE") or row.get("warehouse") or ""),
                    "credits": float(row.get("CREDITS") or row.get("credits") or 0.0),
                }
                for row in team_rows
            ],
            conflict_cols=["day", "team", "warehouse"],
            update_cols=["credits"],
        )

        expensive = self._query_fn(
            settings, EXPENSIVE_QUERIES_SQL, {"day": day, "limit": settings.snowflake_top_n}
        )
        long_running = self._query_fn(
            settings, LONG_RUNNING_SQL, {"day": day, "limit": settings.snowflake_top_n}
        )
        sample_rows = [
            _sample_row(day, "expensive", row) for row in expensive
        ] + [
            _sample_row(day, "long_running", row) for row in long_running
        ]
        upsert_rows(
            session,
            SnowflakeQuerySample,
            sample_rows,
            conflict_cols=["day", "kind", "query_id"],
            update_cols=[
                "user_name",
                "job_tag",
                "warehouse",
                "seconds",
                "credits",
                "query_text",
            ],
        )

        cortex_rows = self._query_fn(settings, CORTEX_SQL, {"day": day})
        upsert_rows(
            session,
            SnowflakeCortexDaily,
            [
                {
                    "day": row.get("DAY") or row.get("day") or day,
                    "user_name": str(row.get("USER_NAME") or row.get("user_name") or ""),
                    "token_credits": float(
                        row.get("TOKEN_CREDITS") or row.get("token_credits") or 0.0
                    ),
                }
                for row in cortex_rows
            ],
            conflict_cols=["day", "user_name"],
            update_cols=["token_credits"],
        )


def _sample_row(day: date, kind: str, row: dict[str, Any]) -> dict[str, Any]:
    def g(*keys: str, default: Any = None) -> Any:
        for key in keys:
            if key in row and row[key] is not None:
                return row[key]
        return default

    return {
        "day": day,
        "kind": kind,
        "query_id": str(g("QUERY_ID", "query_id", default="")),
        "user_name": g("USER_NAME", "user_name"),
        "job_tag": g("JOB_TAG", "job_tag"),
        "warehouse": g("WAREHOUSE", "warehouse"),
        "seconds": float(g("SECONDS", "seconds", default=0.0) or 0.0),
        "credits": float(g("CREDITS", "credits", default=0.0) or 0.0),
        "query_text": g("QUERY_TEXT", "query_text"),
    }


def run_snowflake_query(
    settings: Settings,
    sql: str,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    import snowflake.connector

    conn = snowflake.connector.connect(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        role=settings.snowflake_role,
        warehouse=settings.snowflake_warehouse,
    )
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql, params)
            columns = [col[0] for col in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            cur.close()
    finally:
        conn.close()
