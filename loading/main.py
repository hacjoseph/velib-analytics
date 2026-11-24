
from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import duckdb

logger = logging.getLogger("loading")

SOURCES: tuple[str, ...] = ("station_information", "station_status", "weather_hourly")
RAW_SCHEMA = "raw"
BATCH_SIZE = 200


class ConfigError(ValueError):
    """Raised when the environment does not contain a valid configuration."""


@dataclass(frozen=True, slots=True)
class LoaderSettings:
    duckdb_path: Path
    s3_bucket: str
    s3_endpoint: str
    s3_use_ssl: bool
    s3_region: str
    access_key: str
    secret_key: str
    raw_prefix: str
    log_level: str

    @classmethod
    def from_env(cls) -> LoaderSettings:
        access_key = os.environ.get("OBJECT_STORAGE_ACCESS_KEY", "").strip()
        secret_key = os.environ.get("OBJECT_STORAGE_SECRET_KEY", "").strip()
        if not access_key or not secret_key:
            raise ConfigError(
                "OBJECT_STORAGE_ACCESS_KEY and OBJECT_STORAGE_SECRET_KEY must be set"
            )
        endpoint_url = os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000").strip()
        parsed = urlparse(endpoint_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ConfigError(f"S3_ENDPOINT_URL must look like http://host:port, got {endpoint_url!r}")

        return cls(
            duckdb_path=Path(os.environ.get("DUCKDB_PATH", "data/warehouse/velib.duckdb")),
            s3_bucket=os.environ.get("S3_BUCKET", "velib-raw").strip(),
            s3_endpoint=parsed.netloc,
            s3_use_ssl=parsed.scheme == "https",
            s3_region=os.environ.get("S3_REGION", "us-east-1").strip(),
            access_key=access_key,
            secret_key=secret_key,
            raw_prefix=os.environ.get("RAW_PREFIX", "raw").strip("/"),
            log_level=os.environ.get("LOG_LEVEL", "INFO").strip().upper(),
        )


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stdout,
    )
    logging.Formatter.converter = time.gmtime


def sql_literal(value: str) -> str:
    """Quote a value as a SQL string literal (escapes single quotes)."""
    return "'" + value.replace("'", "''") + "'"


def connect(settings: LoaderSettings) -> duckdb.DuckDBPyConnection:
    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(settings.duckdb_path))
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    
    con.execute(f"""
        CREATE SECRET object_storage (
            TYPE s3,
            KEY_ID {sql_literal(settings.access_key)},
            SECRET {sql_literal(settings.secret_key)},
            REGION {sql_literal(settings.s3_region)},
            ENDPOINT {sql_literal(settings.s3_endpoint)},
            URL_STYLE 'path',
            USE_SSL {"true" if settings.s3_use_ssl else "false"}
        )
    """)
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
    return con


def ensure_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            source_file VARCHAR PRIMARY KEY,   -- lineage + guard against duplicates
            loaded_at   TIMESTAMPTZ NOT NULL,
            payload     JSON NOT NULL
        )
    """)


def list_remote_files(con: duckdb.DuckDBPyConnection, settings: LoaderSettings, source: str) -> list[str]:
    pattern = f"s3://{settings.s3_bucket}/{settings.raw_prefix}/*/{source}/dt=*/*.json.gz"
    rows = con.execute(f"SELECT file FROM glob({sql_literal(pattern)})").fetchall()
    return [row[0] for row in rows]


def insert_batch(con: duckdb.DuckDBPyConnection, table: str, files: list[str]) -> None:
    file_list = "[" + ", ".join(sql_literal(f) for f in files) + "]"
    con.execute("BEGIN TRANSACTION")
    try:
        result = con.execute(f"""
            INSERT INTO {table} (source_file, loaded_at, payload)
            SELECT filename, current_timestamp, json
            FROM read_json_objects({file_list}, format = 'auto', filename = true)
        """).fetchone()
        inserted = result[0] if result else 0
        # Each raw file holds exactly one JSON document: anything else is a bug upstream.
        if inserted != len(files):
            raise RuntimeError(f"expected {len(files)} rows, got {inserted}")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


def load_source(con: duckdb.DuckDBPyConnection, settings: LoaderSettings, source: str) -> int:
    table = f"{RAW_SCHEMA}.{source}"
    ensure_table(con, table)

    remote_files = list_remote_files(con, settings, source)
    already_loaded = {row[0] for row in con.execute(f"SELECT source_file FROM {table}").fetchall()}
    new_files = sorted(f for f in remote_files if f not in already_loaded)

    for start in range(0, len(new_files), BATCH_SIZE):
        batch = new_files[start : start + BATCH_SIZE]
        insert_batch(con, table, batch)
        logger.debug("source=%s batch_loaded=%d", source, len(batch))

    return len(new_files)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    try:
        settings = LoaderSettings.from_env()
    except ConfigError as exc:
        configure_logging("INFO")
        logger.error("status=config_error error=%s", exc)
        return 2
    configure_logging(settings.log_level)

    unknown = [s for s in argv if s not in SOURCES]
    if unknown:
        logger.error("status=config_error unknown_sources=%s valid=%s", unknown, list(SOURCES))
        return 2
    sources = argv or list(SOURCES)

    try:
        con = connect(settings)
    except duckdb.Error:
        logger.exception("status=failed step=connect path=%s", settings.duckdb_path)
        return 1

    failed: list[str] = []
    try:
        for source in sources:
            started = time.monotonic()
            try:
                count = load_source(con, settings, source)
            except (duckdb.Error, RuntimeError):
                logger.exception("source=%s status=failed", source)
                failed.append(source)
                continue
            logger.info(
                "source=%s status=ok new_files=%d duration_s=%.1f",
                source, count, time.monotonic() - started,
            )
    finally:
        con.close()

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())