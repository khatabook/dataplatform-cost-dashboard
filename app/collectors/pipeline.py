from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

import httpx
from sqlalchemy.orm import Session

from app.collectors.upsert import upsert_rows
from app.config import Settings
from app.db.models import PipelineRunsDaily


class PipelineCollector:
    name = "pipeline"

    def __init__(
        self,
        state_fn: Callable[..., str | None] | None = None,
    ) -> None:
        self._state_fn = state_fn or fetch_airflow_dag_state

    def configured(self, settings: Settings) -> bool:
        return bool(settings.pipeline_dag_list())

    def collect(self, session: Session, settings: Settings, day: date) -> None:
        rows: list[dict[str, Any]] = []
        for dag in settings.pipeline_dag_list():
            dag_id = str(dag.get("dag_id") or "")
            destination = str(dag.get("destination") or "unknown")
            if not dag_id:
                continue
            state = None
            if settings.airflow_configured():
                try:
                    state = self._state_fn(settings, dag_id, day)
                except Exception as exc:
                    state = f"error:{exc}"
            rows.append(
                {
                    "day": day,
                    "dag_id": dag_id,
                    "destination": destination,
                    "events": dag.get("events"),
                    "airflow_state": state,
                }
            )
        upsert_rows(
            session,
            PipelineRunsDaily,
            rows,
            conflict_cols=["day", "dag_id"],
            update_cols=["destination", "events", "airflow_state"],
        )


def fetch_airflow_dag_state(settings: Settings, dag_id: str, day: date) -> str | None:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    base = settings.airflow_api_url.rstrip("/")
    # Airflow 2/3 stable API
    url = f"{base}/api/v1/dags/{dag_id}/dagRuns"
    params = {
        "execution_date_gte": start.isoformat(),
        "execution_date_lte": end.isoformat(),
        "order_by": "-execution_date",
        "limit": 1,
    }
    auth = None
    if settings.airflow_api_user:
        auth = (settings.airflow_api_user, settings.airflow_api_password)
    with httpx.Client(timeout=30.0, auth=auth) as client:
        response = client.get(url, params=params)
        if response.status_code == 404:
            return "not_found"
        response.raise_for_status()
        payload = response.json()
    runs = payload.get("dag_runs") or payload.get("dagRuns") or []
    if not runs:
        return "no_run"
    return str(runs[0].get("state") or "unknown")
