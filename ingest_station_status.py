import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"
RAW_DIR = Path("data/raw/velib/station_status")
TIMEOUT_SECONDS = 10

logger = logging.getLogger("ingest_station_status")

# Construit une session avec des paramètres de retry
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

# Récupère et vérifie la donnée de l'API
def fetch_station_status(session: requests.Session) -> bytes:
    response = session.get(URL, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    stations = response.json().get("data", {}).get("stations", [])
    if not stations:
        raise ValueError("API answered but returned no stations")

    logger.info("Fetched %d stations", len(stations))
    return response.content

# Enregistre le contenu brut dans un fichier
def save_raw(content: bytes, fetched_at: datetime) -> Path:
    partition_dir = RAW_DIR / f"dt={fetched_at:%Y-%m-%d}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    file_path = partition_dir / f"station_status_{fetched_at:%Y%m%dT%H%M%SZ}.json"
    file_path.write_bytes(content)
    return file_path

# Point d'entrée principal du script
def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    fetched_at = datetime.now(timezone.utc)

    try:
        with build_session() as session:
            content = fetch_station_status(session)
        file_path = save_raw(content, fetched_at)
    except Exception:
        logger.exception("Ingestion failed")
        return 1

    logger.info("Saved %d bytes to %s", len(content), file_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())