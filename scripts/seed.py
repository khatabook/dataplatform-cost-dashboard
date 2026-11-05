from __future__ import annotations

import random
from datetime import date, timedelta

from app.db.models import (
    BiActivityDaily,
    InfraCostDaily,
    PipelineRunsDaily,
    RudderstackS3Daily,
    SnowflakeCortexDaily,
    SnowflakeQuerySample,
    SnowflakeTeamUsageDaily,
)
from app.db.session import SessionLocal, engine
from app.db.models import Base


TEAMS = ["data-engineering", "analytics", "data-science", "product"]
WAREHOUSES = {
    "data-engineering": ["DE_WH", "ETL_WH"],
    "analytics": ["ANALYTICS_WH", "REPORTING_WH"],
    "data-science": ["DS_WH"],
    "product": ["PRODUCT_WH"],
}
USERS = ["alice@khatabook.com", "bob@khatabook.com", "carol@khatabook.com", "dave@khatabook.com"]
DASHBOARDS = [
    ("1", "Lending Overview"),
    ("2", "Collections Daily"),
    ("3", "Product Funnel"),
    ("4", "UW Monitoring"),
    ("5", "Cost Alerts"),
]


def seed(days: int = 28) -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        session.query(BiActivityDaily).delete()
        session.query(PipelineRunsDaily).delete()
        session.query(RudderstackS3Daily).delete()
        session.query(SnowflakeCortexDaily).delete()
        session.query(SnowflakeQuerySample).delete()
        session.query(SnowflakeTeamUsageDaily).delete()
        session.query(InfraCostDaily).delete()

        today = date.today()
        rng = random.Random(42)
        for offset in range(days, 0, -1):
            day = today - timedelta(days=offset)

            for service, base in [
                ("airflow", 42.0),
                ("rudderstack", 85.0),
                ("redash", 12.0),
            ]:
                cpu = base * 0.45 + rng.uniform(-2, 2)
                ram = base * 0.35 + rng.uniform(-1, 1)
                pv = base * 0.15 + rng.uniform(-0.5, 0.5)
                network = base * 0.05
                session.add(
                    InfraCostDaily(
                        service=service,
                        day=day,
                        cpu_usd=round(cpu, 2),
                        ram_usd=round(ram, 2),
                        pv_usd=round(pv, 2),
                        network_usd=round(network, 2),
                        total_usd=round(cpu + ram + pv + network, 2),
                    )
                )

            for team in TEAMS:
                for warehouse in WAREHOUSES[team]:
                    session.add(
                        SnowflakeTeamUsageDaily(
                            day=day,
                            team=team,
                            warehouse=warehouse,
                            credits=round(rng.uniform(5, 80), 2),
                        )
                    )

            for i, user in enumerate(USERS[:3]):
                session.add(
                    SnowflakeQuerySample(
                        day=day,
                        kind="expensive",
                        query_id=f"exp-{day.isoformat()}-{i}",
                        user_name=user,
                        job_tag=f"job_{i}",
                        warehouse="DE_WH",
                        seconds=rng.uniform(30, 600),
                        credits=round(rng.uniform(1, 25), 2),
                        query_text=f"SELECT * FROM big_table_{i} WHERE dt = '{day}'",
                    )
                )
                session.add(
                    SnowflakeQuerySample(
                        day=day,
                        kind="long_running",
                        query_id=f"long-{day.isoformat()}-{i}",
                        user_name=user,
                        job_tag=f"etl_{i}",
                        warehouse="ETL_WH",
                        seconds=rng.uniform(600, 7200),
                        credits=round(rng.uniform(0.1, 5), 2),
                        query_text=f"MERGE INTO fact_{i} ...",
                    )
                )

            for user in USERS[:2]:
                session.add(
                    SnowflakeCortexDaily(
                        day=day,
                        user_name=user,
                        token_credits=round(rng.uniform(0.5, 12), 2),
                    )
                )

            session.add(
                RudderstackS3Daily(
                    day=day,
                    bucket="kb-rudderstack-events",
                    objects=1_000_000 + offset * 1000,
                    bytes=50_000_000_000 + offset * 10_000_000,
                    put_requests=rng.randint(80_000, 150_000),
                    put_usd=round(rng.uniform(8, 22), 2),
                    volume_source="seed",
                )
            )

            for dag_id, destination in [
                ("rudderstack_s3_snowflake", "snowflake"),
                ("clevertap_set_user_properties", "clevertap"),
            ]:
                session.add(
                    PipelineRunsDaily(
                        day=day,
                        dag_id=dag_id,
                        destination=destination,
                        events=rng.randint(100_000, 500_000) if destination == "snowflake" else None,
                        airflow_state=rng.choice(["success", "success", "success", "failed"]),
                    )
                )

            for tool in ("redash", "tableau"):
                for user in USERS:
                    for object_id, object_name in DASHBOARDS:
                        # Tableau: cumulative-looking counts that grow over days
                        if tool == "tableau":
                            base = int(object_id) * 1000 + USERS.index(user) * 100
                            views = base + (days - offset) * rng.randint(1, 8)
                        else:
                            views = rng.randint(0, 20)
                        if views == 0 and tool == "redash":
                            continue
                        session.add(
                            BiActivityDaily(
                                tool=tool,
                                day=day,
                                user_name=user,
                                object_id=object_id,
                                object_name=object_name,
                                view_count=views,
                            )
                        )

        session.commit()
        print(f"Seeded {days} days of sample cost data.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
