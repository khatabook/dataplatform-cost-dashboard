from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.collectors.upsert import upsert_rows
from app.config import Settings
from app.db.models import RudderstackS3Daily


class RudderstackS3Collector:
    name = "rudderstack_s3"

    def __init__(
        self,
        metrics_fn: Callable[..., dict[str, Any]] | None = None,
        put_cost_fn: Callable[..., float] | None = None,
    ) -> None:
        self._metrics_fn = metrics_fn or fetch_s3_metrics
        self._put_cost_fn = put_cost_fn or fetch_put_cost_from_athena

    def configured(self, settings: Settings) -> bool:
        return bool(settings.rudderstack_bucket_list())

    def collect(self, session: Session, settings: Settings, day: date) -> None:
        rows: list[dict[str, Any]] = []
        for bucket in settings.rudderstack_bucket_list():
            metrics = self._metrics_fn(settings, bucket, day)
            put_usd = 0.0
            if settings.athena_configured():
                try:
                    put_usd = float(self._put_cost_fn(settings, bucket, day) or 0.0)
                except Exception:
                    put_usd = 0.0
            rows.append(
                {
                    "day": day,
                    "bucket": bucket,
                    "objects": int(metrics.get("objects") or 0),
                    "bytes": int(metrics.get("bytes") or 0),
                    "put_requests": int(metrics.get("put_requests") or 0),
                    "put_usd": put_usd,
                    "volume_source": str(metrics.get("volume_source") or "unknown"),
                }
            )
        upsert_rows(
            session,
            RudderstackS3Daily,
            rows,
            conflict_cols=["day", "bucket"],
            update_cols=["objects", "bytes", "put_requests", "put_usd", "volume_source"],
        )


def fetch_s3_metrics(settings: Settings, bucket: str, day: date) -> dict[str, Any]:
    import boto3

    cw = boto3.client("cloudwatch", region_name=settings.aws_region)
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    def metric(name: str, statistic: str = "Sum", extra_dims: list[dict] | None = None) -> float:
        dims = [{"Name": "BucketName", "Value": bucket}]
        if extra_dims:
            dims.extend(extra_dims)
        resp = cw.get_metric_statistics(
            Namespace="AWS/S3",
            MetricName=name,
            Dimensions=dims,
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=[statistic],
        )
        points = resp.get("Datapoints") or []
        if not points:
            return 0.0
        return float(points[0].get(statistic) or 0.0)

    objects = metric("NumberOfObjects", "Average", [{"Name": "StorageType", "Value": "AllStorageTypes"}])
    bytes_ = metric("BucketSizeBytes", "Average", [{"Name": "StorageType", "Value": "StandardStorage"}])
    put_requests = metric(
        "AllRequests",
        "Sum",
        [{"Name": "FilterId", "Value": "EntireBucket"}],
    )
    # Prefer PutRequests when a request metric filter exists; AllRequests is a fallback.
    put_specific = metric(
        "PutRequests",
        "Sum",
        [{"Name": "FilterId", "Value": "EntireBucket"}],
    )
    volume_source = "cloudwatch"
    if put_specific > 0:
        put_requests = put_specific
        volume_source = "cloudwatch_put"
    elif put_requests == 0 and objects == 0 and bytes_ == 0:
        volume_source = "cloudwatch_empty"

    return {
        "objects": int(objects),
        "bytes": int(bytes_),
        "put_requests": int(put_requests),
        "volume_source": volume_source,
    }


def fetch_put_cost_from_athena(settings: Settings, bucket: str, day: date) -> float:
    import time

    import boto3

    athena = boto3.client("athena", region_name=settings.aws_region)
    day_str = day.isoformat()
    sql = f"""
    SELECT COALESCE(SUM(line_item_unblended_cost), 0) AS put_usd
    FROM {settings.athena_database}.{settings.athena_table}
    WHERE line_item_product_code = 'AmazonS3'
      AND line_item_resource_id LIKE '%{bucket}%'
      AND (
            line_item_operation LIKE '%PutObject%'
         OR line_item_usage_type LIKE '%PutObject%'
         OR product_product_family = 'API Request'
      )
      AND line_item_usage_start_date >= TIMESTAMP '{day_str} 00:00:00'
      AND line_item_usage_start_date < TIMESTAMP '{day_str} 00:00:00' + INTERVAL '1' DAY
    """
    start = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": settings.athena_database},
        ResultConfiguration={"OutputLocation": settings.athena_output},
        WorkGroup=settings.athena_workgroup,
    )
    qid = start["QueryExecutionId"]
    for _ in range(60):
        status = athena.get_query_execution(QueryExecutionId=qid)
        state = status["QueryExecution"]["Status"]["State"]
        if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            break
        time.sleep(2)
    if state != "SUCCEEDED":
        reason = status["QueryExecution"]["Status"].get("StateChangeReason", state)
        raise RuntimeError(f"Athena query failed: {reason}")

    result = athena.get_query_results(QueryExecutionId=qid)
    rows = result.get("ResultSet", {}).get("Rows", [])
    if len(rows) < 2:
        return 0.0
    value = rows[1]["Data"][0].get("VarCharValue", "0")
    return float(value or 0.0)
