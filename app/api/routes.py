from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import parse_range
from app.config import get_settings
from app.db.models import (
    BiActivityDaily,
    CollectionRun,
    InfraCostDaily,
    PipelineRunsDaily,
    RudderstackS3Daily,
    SnowflakeCortexDaily,
    SnowflakeQuerySample,
    SnowflakeTeamUsageDaily,
)
from app.db.session import get_db

router = APIRouter(prefix="/api")


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/overview")
def overview(
    rng: tuple[date, date] = Depends(parse_range),
    db: Session = Depends(get_db),
) -> dict:
    start, end = rng
    settings = get_settings()
    credit_usd = settings.snowflake_credit_usd

    infra = db.execute(
        select(
            InfraCostDaily.day,
            InfraCostDaily.service,
            func.sum(InfraCostDaily.total_usd),
        )
        .where(InfraCostDaily.day >= start, InfraCostDaily.day <= end)
        .group_by(InfraCostDaily.day, InfraCostDaily.service)
    ).all()

    snow = db.execute(
        select(SnowflakeTeamUsageDaily.day, func.sum(SnowflakeTeamUsageDaily.credits))
        .where(SnowflakeTeamUsageDaily.day >= start, SnowflakeTeamUsageDaily.day <= end)
        .group_by(SnowflakeTeamUsageDaily.day)
    ).all()

    s3 = db.execute(
        select(RudderstackS3Daily.day, func.sum(RudderstackS3Daily.put_usd))
        .where(RudderstackS3Daily.day >= start, RudderstackS3Daily.day <= end)
        .group_by(RudderstackS3Daily.day)
    ).all()

    by_day: dict[str, dict] = {}

    def bucket(day: date) -> dict:
        key = day.isoformat()
        if key not in by_day:
            by_day[key] = {
                "day": key,
                "snowflake_usd": 0.0,
                "airflow_usd": 0.0,
                "rudderstack_usd": 0.0,
                "redash_usd": 0.0,
                "rudderstack_s3_put_usd": 0.0,
                "total_usd": 0.0,
            }
        return by_day[key]

    for day, service, total in infra:
        row = bucket(day)
        key = f"{service}_usd"
        if key in row:
            row[key] += float(total or 0.0)

    for day, credits in snow:
        row = bucket(day)
        row["snowflake_usd"] += float(credits or 0.0) * credit_usd

    for day, put_usd in s3:
        row = bucket(day)
        row["rudderstack_s3_put_usd"] += float(put_usd or 0.0)

    series = []
    for key in sorted(by_day):
        row = by_day[key]
        row["total_usd"] = (
            row["snowflake_usd"]
            + row["airflow_usd"]
            + row["rudderstack_usd"]
            + row["redash_usd"]
            + row["rudderstack_s3_put_usd"]
        )
        series.append(row)

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "credit_usd": credit_usd,
        "series": series,
    }


@router.get("/snowflake")
def snowflake(
    rng: tuple[date, date] = Depends(parse_range),
    db: Session = Depends(get_db),
) -> dict:
    start, end = rng
    team_rows = db.execute(
        select(
            SnowflakeTeamUsageDaily.day,
            SnowflakeTeamUsageDaily.team,
            SnowflakeTeamUsageDaily.warehouse,
            SnowflakeTeamUsageDaily.credits,
        ).where(
            SnowflakeTeamUsageDaily.day >= start,
            SnowflakeTeamUsageDaily.day <= end,
        )
    ).all()

    weekly: dict[tuple, float] = defaultdict(float)
    warehouses: dict[tuple, float] = defaultdict(float)
    for day, team, warehouse, credits in team_rows:
        week = _week_start(day).isoformat()
        weekly[(week, team)] += float(credits or 0.0)
        warehouses[(week, team, warehouse)] += float(credits or 0.0)

    expensive = (
        db.query(SnowflakeQuerySample)
        .filter(
            SnowflakeQuerySample.day >= start,
            SnowflakeQuerySample.day <= end,
            SnowflakeQuerySample.kind == "expensive",
        )
        .order_by(SnowflakeQuerySample.credits.desc())
        .limit(50)
        .all()
    )
    long_running = (
        db.query(SnowflakeQuerySample)
        .filter(
            SnowflakeQuerySample.day >= start,
            SnowflakeQuerySample.day <= end,
            SnowflakeQuerySample.kind == "long_running",
        )
        .order_by(SnowflakeQuerySample.seconds.desc())
        .limit(50)
        .all()
    )
    cortex = db.execute(
        select(
            SnowflakeCortexDaily.user_name,
            func.sum(SnowflakeCortexDaily.token_credits),
        )
        .where(SnowflakeCortexDaily.day >= start, SnowflakeCortexDaily.day <= end)
        .group_by(SnowflakeCortexDaily.user_name)
        .order_by(func.sum(SnowflakeCortexDaily.token_credits).desc())
    ).all()

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "team_weekly": [
            {"week": week, "team": team, "credits": credits}
            for (week, team), credits in sorted(weekly.items())
        ],
        "warehouse_weekly": [
            {"week": week, "team": team, "warehouse": warehouse, "credits": credits}
            for (week, team, warehouse), credits in sorted(warehouses.items())
        ],
        "expensive_queries": [_query_dict(q) for q in expensive],
        "long_running_queries": [_query_dict(q) for q in long_running],
        "cortex": [
            {"user_name": user, "token_credits": float(credits or 0.0)}
            for user, credits in cortex
        ],
    }


def _query_dict(q: SnowflakeQuerySample) -> dict:
    return {
        "day": q.day.isoformat(),
        "query_id": q.query_id,
        "user_name": q.user_name,
        "job_tag": q.job_tag,
        "warehouse": q.warehouse,
        "seconds": q.seconds,
        "credits": q.credits,
        "query_text": q.query_text,
    }


@router.get("/rudderstack")
def rudderstack(
    rng: tuple[date, date] = Depends(parse_range),
    db: Session = Depends(get_db),
) -> dict:
    start, end = rng
    infra = (
        db.query(InfraCostDaily)
        .filter(
            InfraCostDaily.service == "rudderstack",
            InfraCostDaily.day >= start,
            InfraCostDaily.day <= end,
        )
        .order_by(InfraCostDaily.day)
        .all()
    )
    s3 = (
        db.query(RudderstackS3Daily)
        .filter(RudderstackS3Daily.day >= start, RudderstackS3Daily.day <= end)
        .order_by(RudderstackS3Daily.day)
        .all()
    )
    pipelines = (
        db.query(PipelineRunsDaily)
        .filter(PipelineRunsDaily.day >= start, PipelineRunsDaily.day <= end)
        .order_by(PipelineRunsDaily.day.desc(), PipelineRunsDaily.dag_id)
        .all()
    )

    weekly_s3: dict[tuple, dict] = {}
    for row in s3:
        week = _week_start(row.day).isoformat()
        key = (week, row.bucket)
        bucket = weekly_s3.setdefault(
            key,
            {
                "week": week,
                "bucket": row.bucket,
                "objects": 0,
                "bytes": 0,
                "put_requests": 0,
                "put_usd": 0.0,
            },
        )
        bucket["objects"] += int(row.objects or 0)
        bucket["bytes"] += int(row.bytes or 0)
        bucket["put_requests"] += int(row.put_requests or 0)
        bucket["put_usd"] += float(row.put_usd or 0.0)

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "infra": [
            {
                "day": r.day.isoformat(),
                "cpu_usd": r.cpu_usd,
                "ram_usd": r.ram_usd,
                "pv_usd": r.pv_usd,
                "network_usd": r.network_usd,
                "total_usd": r.total_usd,
            }
            for r in infra
        ],
        "s3_weekly": list(weekly_s3.values()),
        "s3_daily": [
            {
                "day": r.day.isoformat(),
                "bucket": r.bucket,
                "objects": r.objects,
                "bytes": r.bytes,
                "put_requests": r.put_requests,
                "put_usd": r.put_usd,
                "volume_source": r.volume_source,
            }
            for r in s3
        ],
        "pipelines": [
            {
                "day": r.day.isoformat(),
                "dag_id": r.dag_id,
                "destination": r.destination,
                "events": r.events,
                "airflow_state": r.airflow_state,
            }
            for r in pipelines
        ],
    }


@router.get("/airflow")
def airflow(
    rng: tuple[date, date] = Depends(parse_range),
    db: Session = Depends(get_db),
) -> dict:
    start, end = rng
    rows = (
        db.query(InfraCostDaily)
        .filter(
            InfraCostDaily.service == "airflow",
            InfraCostDaily.day >= start,
            InfraCostDaily.day <= end,
        )
        .order_by(InfraCostDaily.day)
        .all()
    )
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "series": [
            {
                "day": r.day.isoformat(),
                "cpu_usd": r.cpu_usd,
                "ram_usd": r.ram_usd,
                "pv_usd": r.pv_usd,
                "network_usd": r.network_usd,
                "total_usd": r.total_usd,
            }
            for r in rows
        ],
    }


@router.get("/bi/{tool}")
def bi(
    tool: str,
    rng: tuple[date, date] = Depends(parse_range),
    db: Session = Depends(get_db),
) -> dict:
    if tool not in {"redash", "tableau"}:
        return {"error": "tool must be redash or tableau"}
    start, end = rng
    rows = (
        db.query(BiActivityDaily)
        .filter(
            BiActivityDaily.tool == tool,
            BiActivityDaily.day >= start,
            BiActivityDaily.day <= end,
        )
        .all()
    )

    # Tableau stores cumulative counters; convert to day deltas using previous day.
    if tool == "tableau":
        rows = _tableau_deltas(db, rows, start)

    users: dict[tuple, int] = defaultdict(int)
    objects: dict[tuple, dict] = {}
    active_by_week: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        week = _week_start(row.day).isoformat()
        users[(week, row.user_name)] += int(row.view_count or 0)
        active_by_week[week].add(row.user_name)
        key = (week, row.object_id)
        obj = objects.setdefault(
            key,
            {
                "week": week,
                "object_id": row.object_id,
                "object_name": row.object_name,
                "view_count": 0,
            },
        )
        obj["view_count"] += int(row.view_count or 0)
        if row.object_name:
            obj["object_name"] = row.object_name

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "tool": tool,
        "active_users_weekly": [
            {"week": week, "active_users": len(users)}
            for week, users in sorted(active_by_week.items())
        ],
        "users_weekly": [
            {"week": week, "user_name": user, "view_count": count}
            for (week, user), count in sorted(users.items(), key=lambda x: -x[1])
        ],
        "objects_weekly": sorted(
            objects.values(), key=lambda x: (-x["view_count"], x["week"])
        )[:50],
    }


def _tableau_deltas(
    db: Session, rows: list[BiActivityDaily], start: date
) -> list[BiActivityDaily]:
    """Replace cumulative view_count with day-over-day positive deltas."""
    if not rows:
        return rows
    object_ids = {r.object_id for r in rows}
    prev_day = start - timedelta(days=1)
    prev = (
        db.query(BiActivityDaily)
        .filter(
            BiActivityDaily.tool == "tableau",
            BiActivityDaily.day == prev_day,
            BiActivityDaily.object_id.in_(object_ids),
        )
        .all()
    )
    prev_map = {(r.user_name, r.object_id): int(r.view_count or 0) for r in prev}
    # Also chain within the requested range chronologically.
    last: dict[tuple, int] = dict(prev_map)
    out: list[BiActivityDaily] = []
    for row in sorted(rows, key=lambda r: (r.day, r.object_id, r.user_name)):
        key = (row.user_name, row.object_id)
        current = int(row.view_count or 0)
        delta = max(0, current - last.get(key, 0))
        last[key] = current
        # Mutate a shallow copy-like object via setattr on the ORM instance for response.
        row.view_count = delta
        out.append(row)
    return out


@router.get("/collection-runs")
def collection_runs(
    rng: tuple[date, date] = Depends(parse_range),
    db: Session = Depends(get_db),
) -> dict:
    start, end = rng
    rows = (
        db.query(CollectionRun)
        .filter(CollectionRun.day >= start, CollectionRun.day <= end)
        .order_by(CollectionRun.day.desc(), CollectionRun.source)
        .all()
    )
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "runs": [
            {
                "source": r.source,
                "day": r.day.isoformat(),
                "status": r.status,
                "error": r.error,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in rows
        ],
    }
