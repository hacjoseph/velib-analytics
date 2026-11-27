"""Refresh the dbt warehouse every hour: check source freshness, then build.

`dbt build` runs seeds, models, snapshots and tests in dependency order,
so the SCD2 snapshot is taken after its upstream models and before
`dim_station`. A freshness error (no new data for 3 h) stops the run
before marts are rebuilt. Both tasks use the `duckdb_writer` pool.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, task

from common.pipeline import run_dbt, run_pipeline_module

DUCKDB_POOL = "duckdb_writer"


@dag(
    dag_id="velib_transformation",
    schedule="7 * * * *",  # Offset from the ingestion slots (:00, :15, :30, :45)
    start_date=datetime(2026, 11, 27, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=45),
    default_args={
        "owner": "data-engineering",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "pool": DUCKDB_POOL,
    },
    tags=["velib", "dbt"],
    doc_md=__doc__,
)
def velib_transformation() -> None:
    @task(execution_timeout=timedelta(minutes=5))
    def dbt_source_freshness() -> None:
        """Fail if a source has not received data within its error threshold."""
        run_dbt(["source", "freshness"])

    @task(execution_timeout=timedelta(minutes=30))
    def dbt_build() -> None:
        """Build seeds, models and snapshots and run all tests."""
        run_dbt(["build"])
        
    @task(execution_timeout=timedelta(minutes=10))
    def publish_marts() -> None:
        """Copy the tested marts to the Postgres serving database (BI layer)."""
        run_pipeline_module("serving.main")

    dbt_source_freshness() >> dbt_build() >> publish_marts()


velib_transformation()