"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-11-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("source", "day", name="uq_collection_runs_source_day"),
    )

    op.create_table(
        "infra_cost_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("cpu_usd", sa.Float(), nullable=False),
        sa.Column("ram_usd", sa.Float(), nullable=False),
        sa.Column("pv_usd", sa.Float(), nullable=False),
        sa.Column("network_usd", sa.Float(), nullable=False),
        sa.Column("total_usd", sa.Float(), nullable=False),
        sa.UniqueConstraint("service", "day", name="uq_infra_cost_daily_service_day"),
    )
    op.create_index("ix_infra_cost_daily_day", "infra_cost_daily", ["day"])

    op.create_table(
        "snowflake_team_usage_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("team", sa.String(length=128), nullable=False),
        sa.Column("warehouse", sa.String(length=256), nullable=False),
        sa.Column("credits", sa.Float(), nullable=False),
        sa.UniqueConstraint(
            "day", "team", "warehouse", name="uq_sf_team_usage_day_team_wh"
        ),
    )
    op.create_index("ix_sf_team_usage_day", "snowflake_team_usage_daily", ["day"])

    op.create_table(
        "snowflake_query_samples",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("query_id", sa.String(length=64), nullable=False),
        sa.Column("user_name", sa.String(length=256), nullable=True),
        sa.Column("job_tag", sa.String(length=512), nullable=True),
        sa.Column("warehouse", sa.String(length=256), nullable=True),
        sa.Column("seconds", sa.Float(), nullable=False),
        sa.Column("credits", sa.Float(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "day", "kind", "query_id", name="uq_sf_query_samples_day_kind_qid"
        ),
    )
    op.create_index(
        "ix_sf_query_samples_day_kind", "snowflake_query_samples", ["day", "kind"]
    )

    op.create_table(
        "snowflake_cortex_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("user_name", sa.String(length=256), nullable=False),
        sa.Column("token_credits", sa.Float(), nullable=False),
        sa.UniqueConstraint("day", "user_name", name="uq_sf_cortex_day_user"),
    )
    op.create_index("ix_sf_cortex_day", "snowflake_cortex_daily", ["day"])

    op.create_table(
        "rudderstack_s3_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("bucket", sa.String(length=256), nullable=False),
        sa.Column("objects", sa.BigInteger(), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("put_requests", sa.BigInteger(), nullable=False),
        sa.Column("put_usd", sa.Float(), nullable=False),
        sa.Column("volume_source", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("day", "bucket", name="uq_rudder_s3_day_bucket"),
    )
    op.create_index("ix_rudder_s3_day", "rudderstack_s3_daily", ["day"])

    op.create_table(
        "pipeline_runs_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("dag_id", sa.String(length=256), nullable=False),
        sa.Column("destination", sa.String(length=64), nullable=False),
        sa.Column("events", sa.BigInteger(), nullable=True),
        sa.Column("airflow_state", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("day", "dag_id", name="uq_pipeline_runs_day_dag"),
    )
    op.create_index("ix_pipeline_runs_day", "pipeline_runs_daily", ["day"])

    op.create_table(
        "bi_activity_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tool", sa.String(length=32), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("user_name", sa.String(length=256), nullable=False),
        sa.Column("object_id", sa.String(length=128), nullable=False),
        sa.Column("object_name", sa.String(length=512), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "tool",
            "day",
            "user_name",
            "object_id",
            name="uq_bi_activity_tool_day_user_obj",
        ),
    )
    op.create_index("ix_bi_activity_tool_day", "bi_activity_daily", ["tool", "day"])


def downgrade() -> None:
    op.drop_index("ix_bi_activity_tool_day", table_name="bi_activity_daily")
    op.drop_table("bi_activity_daily")
    op.drop_index("ix_pipeline_runs_day", table_name="pipeline_runs_daily")
    op.drop_table("pipeline_runs_daily")
    op.drop_index("ix_rudder_s3_day", table_name="rudderstack_s3_daily")
    op.drop_table("rudderstack_s3_daily")
    op.drop_index("ix_sf_cortex_day", table_name="snowflake_cortex_daily")
    op.drop_table("snowflake_cortex_daily")
    op.drop_index("ix_sf_query_samples_day_kind", table_name="snowflake_query_samples")
    op.drop_table("snowflake_query_samples")
    op.drop_index("ix_sf_team_usage_day", table_name="snowflake_team_usage_daily")
    op.drop_table("snowflake_team_usage_daily")
    op.drop_index("ix_infra_cost_daily_day", table_name="infra_cost_daily")
    op.drop_table("infra_cost_daily")
    op.drop_table("collection_runs")
