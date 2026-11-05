from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime

from app.collectors.runner import run_collectors


def _parse_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Collect dataplatform cost snapshots")
    parser.add_argument(
        "--source",
        default="all",
        help="Comma-separated sources or 'all' (snowflake,kubecost,rudderstack_s3,pipeline,redash,tableau)",
    )
    parser.add_argument("--from", dest="start", help="YYYY-MM-DD inclusive")
    parser.add_argument("--to", dest="end", help="YYYY-MM-DD inclusive")
    args = parser.parse_args(argv)

    sources = [s.strip() for s in args.source.split(",") if s.strip()]
    start = _parse_day(args.start) if args.start else None
    end = _parse_day(args.end) if args.end else start
    results = run_collectors(sources=sources, start=start, end=end)
    print(json.dumps(results, indent=2))
    return 0 if all(r["status"] in {"ok", "skipped"} for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
