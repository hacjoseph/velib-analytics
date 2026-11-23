import logging
import sys
from datetime import datetime, timezone

import requests

from ingestion.common import build_session, configure_logging, save_raw
from ingestion.sources import SOURCES, Source

TIMEOUT_SECONDS = 10

logger = logging.getLogger("velib_ingestion")


def ingest(source: Source, session: requests.Session) -> None:
    fetched_at = datetime.now(timezone.utc)

    response = session.get(source.url, params=source.params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    record_count = source.validate(response.json())
    file_path = save_raw(response.content, source.domain, source.name, fetched_at)

    logger.info(
        "Source %s: saved %d records (%d bytes raw, %d bytes stored) to %s",
        source.name,
        record_count,
        len(response.content),
        file_path.stat().st_size,
        file_path,
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

    failed: list[str] = []
    with build_session() as session:
        for name in names:
            try:
                ingest(SOURCES[name], session)
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