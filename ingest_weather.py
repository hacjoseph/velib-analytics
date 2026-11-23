import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://api.open-meteo.com/v1/forecast"
VARIABLES = ("temperature_2m", "precipitation", "wind_speed_10m", "weather_code")
PARAMS = {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "hourly": ",".join(VARIABLES),
    "past_days": 1,
    "forecast_days": 1,
    "timezone": "UTC",
}
RAW_DIR = Path("data/raw/weather/hourly")
TIMEOUT_SECONDS = 10

logger = logging.getLogger("ingest_weather")


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


def fetch_weather(session: requests.Session) -> bytes:
    response = session.get(URL, params=PARAMS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    hourly = response.json().get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("API answered but returned no hourly data")

    for variable in VARIABLES:
        values = hourly.get(variable)
        if values is None or len(values) != len(times):
            raise ValueError(
                f"Variable {variable!r} is missing or does not have {len(times)} values"
            )

    logger.info("Fetched %d hours of weather", len(times))
    return response.content


def save_raw(content: bytes, fetched_at: datetime) -> Path:
    partition_dir = RAW_DIR / f"dt={fetched_at:%Y-%m-%d}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    file_path = partition_dir / f"weather_hourly_{fetched_at:%Y%m%dT%H%M%SZ}.json"
    file_path.write_bytes(content)
    return file_path


def main() -> int:
    logging.Formatter.converter = time.gmtime  # log timestamps in UTC
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    fetched_at = datetime.now(timezone.utc)

    try:
        with build_session() as session:
            content = fetch_weather(session)
        file_path = save_raw(content, fetched_at)
    except Exception:
        logger.exception("Ingestion failed")
        return 1

    logger.info("Saved %d bytes to %s", len(content), file_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())