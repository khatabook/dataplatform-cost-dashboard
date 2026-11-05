from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CollectionRun(Base):
    __tablename__ = "collection_runs"
    __table_args__ = (
        UniqueConstraint("source", "day", name="uq_collection_runs_source_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InfraCostDaily(Base):
    __tablename__ = "infra_cost_daily"
    __table_args__ = (
        UniqueConstraint("service", "day", name="uq_infra_cost_daily_service_day"),
        Index("ix_infra_cost_daily_day", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    cpu_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ram_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pv_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    network_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class SnowflakeTeamUsageDaily(Base):
    __tablename__ = "snowflake_team_usage_daily"
    __table_args__ = (
        UniqueConstraint(
            "day", "team", "warehouse", name="uq_sf_team_usage_day_team_wh"
        ),
        Index("ix_sf_team_usage_day", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    team: Mapped[str] = mapped_column(String(128), nullable=False)
    warehouse: Mapped[str] = mapped_column(String(256), nullable=False)
    credits: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class SnowflakeQuerySample(Base):
    __tablename__ = "snowflake_query_samples"
    __table_args__ = (
        UniqueConstraint(
            "day",
            "kind",
            "query_id",
            name="uq_sf_query_samples_day_kind_qid",
        ),
        Index("ix_sf_query_samples_day_kind", "day", "kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    query_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    job_tag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    warehouse: Mapped[str | None] = mapped_column(String(256), nullable=True)
    seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    credits: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class SnowflakeCortexDaily(Base):
    __tablename__ = "snowflake_cortex_daily"
    __table_args__ = (
        UniqueConstraint("day", "user_name", name="uq_sf_cortex_day_user"),
        Index("ix_sf_cortex_day", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    user_name: Mapped[str] = mapped_column(String(256), nullable=False)
    token_credits: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class RudderstackS3Daily(Base):
    __tablename__ = "rudderstack_s3_daily"
    __table_args__ = (
        UniqueConstraint("day", "bucket", name="uq_rudder_s3_day_bucket"),
        Index("ix_rudder_s3_day", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    bucket: Mapped[str] = mapped_column(String(256), nullable=False)
    objects: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    put_requests: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    put_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    volume_source: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)


class PipelineRunsDaily(Base):
    __tablename__ = "pipeline_runs_daily"
    __table_args__ = (
        UniqueConstraint("day", "dag_id", name="uq_pipeline_runs_day_dag"),
        Index("ix_pipeline_runs_day", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    dag_id: Mapped[str] = mapped_column(String(256), nullable=False)
    destination: Mapped[str] = mapped_column(String(64), nullable=False)
    events: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    airflow_state: Mapped[str | None] = mapped_column(String(64), nullable=True)


class BiActivityDaily(Base):
    __tablename__ = "bi_activity_daily"
    __table_args__ = (
        UniqueConstraint(
            "tool",
            "day",
            "user_name",
            "object_id",
            name="uq_bi_activity_tool_day_user_obj",
        ),
        Index("ix_bi_activity_tool_day", "tool", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tool: Mapped[str] = mapped_column(String(32), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    user_name: Mapped[str] = mapped_column(String(256), nullable=False)
    object_id: Mapped[str] = mapped_column(String(128), nullable=False)
    object_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
