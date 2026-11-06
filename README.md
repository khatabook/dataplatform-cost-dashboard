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

Copy `.env.example` to `.env` for local collector credentials. Vault is not required locally; the entrypoint skips `/vault/secrets/secrets.txt` when missing.

## Architecture

```
Vault KV  --(Agent Injector)--> /vault/secrets/secrets.txt
                                      |
                                      v
CronJob / API entrypoint exports env --> collectors / FastAPI --> Postgres
Browser ------------------------------------------------------> FastAPI UI
```

Collectors: `snowflake`, `kubecost`, `rudderstack_s3`, `pipeline`, `redash`, `tableau`.

## Credentials (Vault)

Secrets are **not** stored in a Kubernetes Secret. The chart enables the Vault Agent Injector, which writes:

| | Default |
| --- | --- |
| Path | `private/data/prod-dataplatform/dataplatform-cost-dashboard` |
| Role | `prod-dataplatform-dataplatform-cost-dashboard` |
| File | `/vault/secrets/secrets.txt` |

`scripts/entrypoint.sh` parses that file (KEY=VALUE or Go `data: map[...]`) and exports the keys before starting uvicorn, alembic, or the collector.

Required / optional keys are listed in [`charts/dataplatform-cost-dashboard/vault.example.yaml`](charts/dataplatform-cost-dashboard/vault.example.yaml).

Example:

```bash
vault kv put private/prod-dataplatform/dataplatform-cost-dashboard \
  DATABASE_URL='postgresql+psycopg2://...' \
  SNOWFLAKE_ACCOUNT='...' \
  SNOWFLAKE_USER='...' \
  SNOWFLAKE_PASSWORD='...' \
  SNOWFLAKE_WAREHOUSE='...'
```

Ensure the Kubernetes auth role allows the chart service account in `prod-dataplatform` to read that path (same pattern as other dataplatform services).

Non-secret settings (Kubecost URL, Athena table names, pipeline DAG list, etc.) stay in the Helm ConfigMap via `values.yaml` → `config`.

## Deploy to Kubernetes

1. Put credentials in Vault (see above).
2. Build and push the image.
3. Install the chart:

```bash
helm upgrade --install dataplatform-cost-dashboard \
  ./charts/dataplatform-cost-dashboard \
  -n prod-dataplatform \
  --set image.tag=<tag>
```

The Deployment runs `alembic upgrade head` as an init container (after Vault pre-populate). A CronJob runs `python -m app.collect --source all` daily (default `30 1 * * *`).

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
