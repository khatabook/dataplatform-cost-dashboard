from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors.snowflake_collector import SnowflakeCollector
from app.config import Settings
from app.db.models import Base, SnowflakeCortexDaily, SnowflakeQuerySample, SnowflakeTeamUsageDaily


def test_snowflake_collector_upserts_from_query_fn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def fake_query(settings, sql, params):
        if "warehouse_metering_history" in sql:
            return [
                {"day": params["day"], "team": "analytics", "warehouse": "ANALYTICS_WH", "credits": 12.5}
            ]
        if "query_attribution_history" in sql:
            return [
                {
                    "query_id": "q1",
                    "user_name": "alice",
                    "job_tag": "job_a",
                    "warehouse": "ANALYTICS_WH",
                    "seconds": 10,
                    "credits": 3.2,
                    "query_text": "select 1",
                }
            ]
        if "total_elapsed_time" in sql and "query_attribution" not in sql:
            return [
                {
                    "query_id": "q2",
                    "user_name": "bob",
                    "job_tag": "etl",
                    "warehouse": "ETL_WH",
                    "seconds": 900,
                    "credits": 0,
                    "query_text": "merge ...",
                }
            ]
        if "cortex_code" in sql:
            return [{"day": params["day"], "user_name": "alice", "token_credits": 1.5}]
        return []

    settings = Settings(snowflake_account="x", snowflake_user="u", snowflake_password="p")
    SnowflakeCollector(query_fn=fake_query).collect(session, settings, date(2026, 11, 1))
    session.commit()

    assert session.query(SnowflakeTeamUsageDaily).count() == 1
    assert session.query(SnowflakeQuerySample).count() == 2
    assert session.query(SnowflakeCortexDaily).one().token_credits == 1.5
