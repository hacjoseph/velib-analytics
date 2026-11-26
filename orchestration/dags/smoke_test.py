"""Smoke-test DAG: validates that Airflow can parse a DAG and run a task."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="smoke_test",
    schedule=None,
    start_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["maintenance"],
    doc_md=__doc__,
)
def smoke_test() -> None:
    @task
    def say_hello() -> str:
        logger.info("Airflow is up and running tasks.")
        return "ok"

    say_hello()


smoke_test()