# Dataplatform Cost Dashboard

Kubernetes service that stores daily cost snapshots for the data platform and serves a dashboard over any stored date range.

## What it tracks

| Source | Metrics |
| --- | --- |
| Snowflake | Team weekly credits (`warehouse_team_mapping`), expensive queries, long-running queries by user/job tag, Cortex Code |
| Rudderstack | Kubecost infra cost, S3 weekly volume + PUT cost (CloudWatch + Athena CUR), DAGs to Snowflake / CleverTap |
| Airflow | Kubecost CPU / RAM / PV / network |
| Redash | Weekly users and most-viewed dashboards (metadata DB `events`) |
| Tableau | Same layout via REST PAT; cumulative view counts stored daily and differenced in the API |

The UI reads **Postgres only**. Collectors write closed-day rows. Missing credentials mark a source as `skipped`.

## Local development

```bash
docker compose up --build
```

Opens [http://localhost:8000](http://localhost:8000) with 28 days of seeded data.

Useful commands:

```bash
# Backfill / collect for a day
docker compose run --rm api python -m app.collect --source all --from 2026-11-01 --to 2026-11-03

# Unit tests
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Copy `.env.example` to `.env` for local collector credentials.

## Architecture

```
CronJob (daily) --> collectors --> Postgres
Browser ----------> FastAPI -----> Postgres
                     \--> React static assets
```

Collectors: `snowflake`, `kubecost`, `rudderstack_s3`, `pipeline`, `redash`, `tableau`.

## Deploy to Kubernetes

1. Create a Postgres database and a secret named `dataplatform-cost-dashboard` with at least `DATABASE_URL`. Add Snowflake, Redash, Tableau, Airflow, and AWS keys as needed (see `charts/.../values.yaml`).
2. Build and push the image.
3. Install the chart:

```bash
helm upgrade --install dataplatform-cost-dashboard \
  ./charts/dataplatform-cost-dashboard \
  -n prod-dataplatform \
  --set image.tag=<tag>
```

The Deployment runs `alembic upgrade head` as an init container. A CronJob runs `python -m app.collect --source all` daily (default `30 1 * * *`).

Point `KUBECOST_SERVICES` at your `infra-service` labels (`airflow,rudderstack,redash`). Set `RUDDERSTACK_S3_BUCKETS` to a comma-separated bucket list. Tableau is usage-only (not in Kubecost).

## API

- `GET /api/health`
- `GET /api/overview?from=&to=`
- `GET /api/snowflake?from=&to=`
- `GET /api/rudderstack?from=&to=`
- `GET /api/airflow?from=&to=`
- `GET /api/bi/redash?from=&to=`
- `GET /api/bi/tableau?from=&to=`
- `GET /api/collection-runs?from=&to=`
