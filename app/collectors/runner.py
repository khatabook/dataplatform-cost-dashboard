from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.collectors.base import record_run
from app.collectors.kubecost import KubecostCollector
from app.collectors.pipeline import PipelineCollector
from app.collectors.redash import RedashCollector
from app.collectors.rudderstack import RudderstackS3Collector
from app.collectors.snowflake_collector import SnowflakeCollector
from app.collectors.tableau import TableauCollector
from app.config import Settings, get_settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

COLLECTORS = [
    SnowflakeCollector(),
    KubecostCollector(),
    RudderstackS3Collector(),
    PipelineCollector(),
    RedashCollector(),
    TableauCollector(),
]


def run_collectors(
    *,
    sources: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
    settings: Settings | None = None,
    session: Session | None = None,
) -> list[dict]:
    settings = settings or get_settings()
    own_session = session is None
    session = session or SessionLocal()
    wanted = {s.lower() for s in sources} if sources else None
    start = start or (date.today() - timedelta(days=1))
    end = end or start
    if end < start:
        raise ValueError("end date must be on or after start date")

    results: list[dict] = []
    try:
        day = start
        while day <= end:
            for collector in COLLECTORS:
                if wanted is not None and collector.name not in wanted and "all" not in wanted:
                    continue
                if not collector.configured(settings):
                    record_run(session, collector.name, day, "skipped", "not configured")
                    session.commit()
                    results.append(
                        {"source": collector.name, "day": day.isoformat(), "status": "skipped"}
                    )
                    continue
                try:
                    collector.collect(session, settings, day)
                    record_run(session, collector.name, day, "ok")
                    session.commit()
                    results.append(
                        {"source": collector.name, "day": day.isoformat(), "status": "ok"}
                    )
                except Exception as exc:  # noqa: BLE001 — record and continue other sources
                    session.rollback()
                    logger.exception("collector %s failed for %s", collector.name, day)
                    record_run(session, collector.name, day, "error", str(exc)[:2000])
                    session.commit()
                    results.append(
                        {
                            "source": collector.name,
                            "day": day.isoformat(),
                            "status": "error",
                            "error": str(exc),
                        }
                    )
            day += timedelta(days=1)
    finally:
        if own_session:
            session.close()
    return results
