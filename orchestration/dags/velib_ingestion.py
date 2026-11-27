"""Collect Velib' and Open-Meteo snapshots every 15 minutes and load them into DuckDB.

One chain per source: `ingest_<source>` writes the raw JSON to object storage,
then `load_<source>` appends the new files to `raw.<source>` in DuckDB.
Loads share the `duckdb_writer` pool (1 slot) because DuckDB allows a single
writer process.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, task

from common.pipeline import run_pipeline_module

SOURCES: tuple[str, ...] = ("station_status", "station_information", "weather_hourly")
DUCKDB_POOL = "duckdb_writer"


@dag(
    dag_id="velib_ingestion",
    schedule="*/30 * * * *",
    start_date=datetime(2026, 11, 27, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=14),
    default_args={
        "owner": "data-engineering",
        "retries": 2,
        "retry_delay": timedelta(minutes=1),
        "retry_exponential_backoff": True,
    },
    tags=["velib", "ingestion"],
    doc_md=__doc__,
)
def velib_ingestion() -> None:
    @task(execution_timeout=timedelta(minutes=5))
    def ingest(source: str) -> None:
        """Fetch one API snapshot and store it raw in object storage."""
        run_pipeline_module("ingestion.main", [source])

    @task(pool=DUCKDB_POOL, execution_timeout=timedelta(minutes=5))
    def load(source: str) -> None:
        """Append the source's new raw files to DuckDB (incremental, idempotent)."""
        run_pipeline_module("loading.main", [source])

    for source in SOURCES:
        ingested = ingest.override(task_id=f"ingest_{source}")(source)
        loaded = load.override(task_id=f"load_{source}")(source)
        ingested >> loaded


velib_ingestion()