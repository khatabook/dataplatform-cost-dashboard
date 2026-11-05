from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Protocol

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import CollectionRun


class Collector(Protocol):
    name: str

    def configured(self, settings: Settings) -> bool: ...

    def collect(self, session: Session, settings: Settings, day: date) -> None: ...


def record_run(
    session: Session,
    source: str,
    day: date,
    status: str,
    error: str | None = None,
) -> None:
    existing = (
        session.query(CollectionRun)
        .filter(CollectionRun.source == source, CollectionRun.day == day)
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if existing is None:
        session.add(
            CollectionRun(
                source=source,
                day=day,
                status=status,
                error=error,
                started_at=now,
                finished_at=now,
            )
        )
    else:
        existing.status = status
        existing.error = error
        existing.finished_at = now
