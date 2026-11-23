import logging
import time
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RAW_ROOT = Path("data/raw")


def configure_logging() -> None:
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )


def build_session() -> requests.Session:
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def save_raw(content: bytes, domain: str, source_name: str, fetched_at: datetime) -> Path:
    partition_dir = RAW_ROOT / domain / source_name / f"dt={fetched_at:%Y-%m-%d}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    file_path = partition_dir / f"{source_name}_{fetched_at:%Y%m%dT%H%M%SZ}.json"
    file_path.write_bytes(content)
    return file_path