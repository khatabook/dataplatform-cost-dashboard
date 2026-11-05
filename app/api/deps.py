from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import HTTPException, Query


def parse_range(
    start: str | None = Query(None, alias="from"),
    end: str | None = Query(None, alias="to"),
) -> tuple[date, date]:
    today = date.today()
    end_day = _parse(end) if end else today - timedelta(days=1)
    start_day = _parse(start) if start else end_day - timedelta(days=27)
    if start_day > end_day:
        raise HTTPException(status_code=400, detail="'from' must be on or before 'to'")
    return start_day, end_day


def _parse(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {value}") from exc
