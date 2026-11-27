"""Helpers to run the Velib pipeline CLIs (isolated venv) from Airflow tasks."""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Collection, Sequence
from pathlib import Path

from airflow.exceptions import AirflowException, AirflowFailException

logger = logging.getLogger(__name__)

VELIB_HOME = Path(os.environ.get("VELIB_HOME", "/opt/velib"))
VELIB_VENV = Path(os.environ.get("VELIB_VENV", "/opt/velib-venv"))
VELIB_PYTHON = VELIB_VENV / "bin" / "python"
DBT_BIN = VELIB_VENV / "bin" / "dbt"
DBT_PROJECT_DIR = VELIB_HOME / "transform"

EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 2  # Convention of the ingestion and loading CLIs


def run_command(
    cmd: Sequence[str],
    cwd: Path,
    *,
    no_retry_exit_codes: Collection[int] = (),
) -> None:
    """Run a command, stream its output to the task log and map its exit code.

    Exit codes listed in `no_retry_exit_codes` fail the task immediately
    (retrying cannot help, e.g. a configuration error). Any other non-zero
    code raises a regular failure so that Airflow applies its retries.
    """
    printable = " ".join(cmd)
    logger.info("Running: %s (cwd=%s)", printable, cwd)

    with subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    ) as process:
        if process.stdout is None:
            raise RuntimeError("Subprocess stdout is not captured")
        for line in process.stdout:
            logger.info(line.rstrip())
        return_code = process.wait()

    if return_code == EXIT_SUCCESS:
        return
    if return_code in no_retry_exit_codes:
        raise AirflowFailException(
            f"'{printable}' exited with code {return_code}; not retrying"
        )
    raise AirflowException(f"'{printable}' failed with exit code {return_code}")


def run_pipeline_module(module: str, args: Sequence[str] = ()) -> None:
    """Run `python -m <module>` from the pipeline venv (ingestion, loading)."""
    run_command(
        [str(VELIB_PYTHON), "-m", module, *args],
        cwd=VELIB_HOME,
        no_retry_exit_codes={EXIT_CONFIG_ERROR},
    )


def run_dbt(args: Sequence[str]) -> None:
    """Run a dbt command in the project directory, without ANSI colors in logs."""
    run_command([str(DBT_BIN), *args, "--no-use-colors"], cwd=DBT_PROJECT_DIR)