from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

VELIB_BASE_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_VARIABLES = ("temperature_2m", "precipitation", "wind_speed_10m", "weather_code")


def validate_gbfs(payload: dict[str, Any]) -> int:
    stations = payload.get("data", {}).get("stations", [])
    if not stations:
        raise ValueError("GBFS payload contains no stations")
    return len(stations)


def validate_open_meteo(payload: dict[str, Any]) -> int:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("Open-Meteo payload contains no hourly data")

    for variable in WEATHER_VARIABLES:
        values = hourly.get(variable)
        if values is None or len(values) != len(times):
            raise ValueError(
                f"Variable {variable!r} is missing or does not have {len(times)} values"
            )
    return len(times)


@dataclass(frozen=True)
class Source:
    name: str
    domain: str
    url: str
    validate: Callable[[dict[str, Any]], int]
    params: dict[str, str | int | float] = field(default_factory=dict)


SOURCES: dict[str, Source] = {
    source.name: source
    for source in (
        Source(
            name="station_information",
            domain="velib",
            url=f"{VELIB_BASE_URL}/station_information.json",
            validate=validate_gbfs,
        ),
        Source(
            name="station_status",
            domain="velib",
            url=f"{VELIB_BASE_URL}/station_status.json",
            validate=validate_gbfs,
        ),
        Source(
            name="weather_hourly",
            domain="weather",
            url=OPEN_METEO_URL,
            validate=validate_open_meteo,
            params={
                "latitude": 48.8566,
                "longitude": 2.3522,
                "hourly": ",".join(WEATHER_VARIABLES),
                "past_days": 1,
                "forecast_days": 1,
                "timezone": "UTC",
            },
        ),
    )
}