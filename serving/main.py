"""Publish the dbt marts from DuckDB to the Postgres serving database (BI layer).

All marts tables are replaced inside a single Postgres transaction, so BI users
never see a mix of old and new tables. The DuckDB warehouse is opened read-only.

Usage: python -m serving.main
Exit codes: 0 = success, 1 = publishing failed, 2 = configuration error.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass

import duckdb

logger = logging.getLogger("serving")

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFIG_ERROR = 2

SOURCE_SCHEMA = "marts"
TARGET_CATALOG = "serving"
TARGET_SCHEMA = "analytics"
PG_SECRET_NAME = "serving_pg"

REQUIRED_ENV_VARS = (
    "DBT_DUCKDB_PATH",
    "ANALYTICS_PG_HOST",
    "ANALYTICS_PG_DATABASE",
    "ANALYTICS_PG_USER",
    "ANALYTICS_PG_PASSWORD",
)
WAREHOUSE_CATALOG = "warehouse"


class ConfigError(Exception):
    """Raised when the environment does not provide a valid configuration."""


@dataclass(frozen=True)
class Settings:
    duckdb_path: str
    pg_host: str
    pg_port: int
    pg_database: str
    pg_user: str
    pg_password: str
    memory_limit: str

    @classmethod
    def from_env(cls) -> Settings:
        missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
        if missing:
            raise ConfigError(f"Missing environment variables: {', '.join(missing)}")
        raw_port = os.environ.get("ANALYTICS_PG_PORT", "5432")
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ConfigError(f"ANALYTICS_PG_PORT must be an integer, got {raw_port!r}") from exc
        return cls(
            duckdb_path=os.environ["DBT_DUCKDB_PATH"],
            pg_host=os.environ["ANALYTICS_PG_HOST"],
            pg_port=port,
            pg_database=os.environ["ANALYTICS_PG_DATABASE"],
            pg_user=os.environ["ANALYTICS_PG_USER"],
            pg_password=os.environ["ANALYTICS_PG_PASSWORD"],
            memory_limit=os.environ.get("DUCKDB_MEMORY_LIMIT", "2GB"),
        )


def sql_literal(value: str) -> str:
    """Quote a value as a SQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def sql_identifier(name: str) -> str:
    """Quote a SQL identifier."""
    return '"' + name.replace('"', '""') + '"'


def list_mart_tables(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Return the base tables of the marts schema in the attached warehouse."""
    rows = con.execute(
        """
        select table_name
        from information_schema.tables
        where table_catalog = ?
          and table_schema = ?
          and table_type = 'BASE TABLE'
        order by table_name
        """,
        [WAREHOUSE_CATALOG, SOURCE_SCHEMA],
    ).fetchall()
    return [row[0] for row in rows]


def attach_serving_database(con: duckdb.DuckDBPyConnection, settings: Settings) -> None:
    """Attach Postgres through a temporary secret (credentials never logged)."""
    con.execute("INSTALL postgres")
    con.execute("LOAD postgres")
    con.execute(
        f"""
        CREATE TEMPORARY SECRET {PG_SECRET_NAME} (
            TYPE postgres,
            HOST {sql_literal(settings.pg_host)},
            PORT {settings.pg_port},
            DATABASE {sql_literal(settings.pg_database)},
            USER {sql_literal(settings.pg_user)},
            PASSWORD {sql_literal(settings.pg_password)}
        )
        """
    )
    con.execute(f"ATTACH '' AS {TARGET_CATALOG} (TYPE postgres, SECRET {PG_SECRET_NAME})")


def publish(settings: Settings) -> None:
    """Replace every marts table in Postgres within one transaction."""
    started = time.monotonic()
    # In-memory instance: each attached database gets its own access mode
    # (a read-only connect() would make every attached database read-only).
    con = duckdb.connect()
    try:
        con.execute(f"SET memory_limit = {sql_literal(settings.memory_limit)}")
        con.execute(
            f"ATTACH {sql_literal(settings.duckdb_path)} AS {WAREHOUSE_CATALOG} (READ_ONLY)"
        )
        tables = list_mart_tables(con)
        if not tables:
            raise RuntimeError(f"No tables found in schema '{SOURCE_SCHEMA}'; run dbt build first")

        attach_serving_database(con, settings)

        con.execute("BEGIN TRANSACTION")
        try:
            for table in tables:
                source = f"{WAREHOUSE_CATALOG}.{SOURCE_SCHEMA}.{sql_identifier(table)}"
                target = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{sql_identifier(table)}"
                con.execute(f"CREATE OR REPLACE TABLE {target} AS SELECT * FROM {source}")
                row_count = con.execute(f"SELECT count(*) FROM {source}").fetchone()[0]
                logger.info("Staged %s.%s (%d rows)", TARGET_SCHEMA, table, row_count)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    finally:
        con.close()

    logger.info(
        "Published %d tables to %s in %.1fs",
        len(tables),
        TARGET_SCHEMA,
        time.monotonic() - started,
    )


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return EXIT_CONFIG_ERROR

    try:
        publish(settings)
    except Exception:
        logger.exception("Publishing failed")
        return EXIT_FAILURE
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())