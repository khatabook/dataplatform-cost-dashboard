from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://cost:cost@localhost:5432/cost_dashboard"

    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_role: str = "ACCOUNTADMIN"
    snowflake_warehouse: str = ""
    snowflake_credit_usd: float = 3.0
    snowflake_top_n: int = 25

    kubecost_base_url: str = "http://kubecost-cost-analyzer.kubecost:9090"
    kubecost_services: str = "airflow,rudderstack,redash"

    aws_region: str = "ap-south-1"
    athena_database: str = "athenacurcfn_prod_platform_kubecost"
    athena_table: str = "prod_platform_kubecost"
    athena_output: str = "s3://prod-platform-kubecost/athena-results/"
    athena_workgroup: str = "primary"
    rudderstack_s3_buckets: str = ""

    airflow_api_url: str = ""
    airflow_api_user: str = ""
    airflow_api_password: str = ""
    pipeline_dags: str = Field(
        default='[{"dag_id":"rudderstack_s3_snowflake","destination":"snowflake"},'
        '{"dag_id":"clevertap_set_user_properties","destination":"clevertap"}]'
    )

    redash_database_url: str = ""
    tableau_server_url: str = ""
    tableau_site: str = ""
    tableau_pat_name: str = ""
    tableau_pat_secret: str = ""

    static_dir: str = "frontend/dist"

    def kubecost_service_list(self) -> list[str]:
        return [s.strip() for s in self.kubecost_services.split(",") if s.strip()]

    def rudderstack_bucket_list(self) -> list[str]:
        return [s.strip() for s in self.rudderstack_s3_buckets.split(",") if s.strip()]

    def pipeline_dag_list(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.pipeline_dags or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return data

    def snowflake_configured(self) -> bool:
        return bool(self.snowflake_account and self.snowflake_user and self.snowflake_password)

    def redash_configured(self) -> bool:
        return bool(self.redash_database_url)

    def tableau_configured(self) -> bool:
        return bool(
            self.tableau_server_url
            and self.tableau_pat_name
            and self.tableau_pat_secret
        )

    def airflow_configured(self) -> bool:
        return bool(self.airflow_api_url)

    def athena_configured(self) -> bool:
        return bool(self.athena_database and self.athena_table and self.athena_output)


@lru_cache
def get_settings() -> Settings:
    return Settings()
