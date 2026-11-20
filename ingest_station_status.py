from datetime import datetime, timezone
from pathlib import Path
import requests

URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"
RAW_DIR = Path("data/raw/velib/station_status")


def main() -> None:
    fetched_at = datetime.now(timezone.utc)
    
    response = requests.get(URL, timeout=10)
    response.raise_for_status()
    
    partition_dir = RAW_DIR / f"dt={fetched_at:%Y-%m-%d}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = partition_dir / f"station_status_{fetched_at:%Y-%m-%dT%H-%M-%S}.json"
    file_path.write_bytes(response.content)
    
    print(f"Saved {len(response.content)} bytes to {file_path}")


if __name__ == "__main__":
    main()