from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors.runner import run_collectors
from app.config import Settings
from app.db.models import Base, CollectionRun


def test_unconfigured_sources_are_skipped():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        kubecost_base_url="",
        kubecost_services="",
        pipeline_dags="[]",
    )
    results = run_collectors(
        sources=["snowflake", "redash", "tableau"],
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        settings=settings,
        session=session,
    )
    assert all(r["status"] == "skipped" for r in results)
    assert session.query(CollectionRun).count() == 3
