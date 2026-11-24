import gzip
import logging
import sys
from datetime import datetime, timezone

import requests

from ingestion.common import build_object_key, build_session, configure_logging
from ingestion.sources import SOURCES, Source
from ingestion.storage import Storage, build_storage

TIMEOUT_SECONDS = 10

logger = logging.getLogger("ingestion")


def ingest(source: Source, session: requests.Session, storage: Storage) -> None:
    fetched_at = datetime.now(timezone.utc)

    response = session.get(source.url, params=source.params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    record_count = source.validate(response.json())

    body = gzip.compress(response.content, mtime=0)
    key = build_object_key(source.domain, source.name, fetched_at)
    location = storage.save(key, body)

    logger.info(
        "Source %s: saved %d records (%d bytes raw, %d bytes stored) to %s",
        source.name,
        record_count,
        len(response.content),
        len(body),
        location,
    )


def main(argv: list[str]) -> int:
    configure_logging()

    names = argv or list(SOURCES)
    unknown = [name for name in names if name not in SOURCES]
    if unknown:
        logger.error(
            "Unknown source(s): %s. Available: %s", ", ".join(unknown), ", ".join(SOURCES)
        )
        return 2

    try:
        storage = build_storage()
    except Exception:
        logger.exception("Could not initialise storage")
        return 2

    failed: list[str] = []
    with build_session() as session:
        for name in names:
            try:
                ingest(SOURCES[name], session, storage)
            except Exception:
                logger.exception("Source %s failed", name)
                failed.append(name)

    if failed:
        logger.error("Run finished with failures: %s", ", ".join(failed))
        return 1

    logger.info("Run finished successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))