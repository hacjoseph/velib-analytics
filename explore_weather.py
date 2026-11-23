import requests

URL = "https://api.open-meteo.com/v1/forecast"
PARAMS = {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "hourly": "temperature_2m,precipitation,wind_speed_10m,weather_code",
    "past_days": 1,
    "forecast_days": 1,
    "timezone": "UTC",
}

response = requests.get(URL, params=PARAMS, timeout=10)
print("HTTP status:", response.status_code)
print("Final URL:", response.url)

payload = response.json()
print("Top-level keys:", list(payload.keys()))
print("Units:", payload["hourly_units"])

hourly = payload["hourly"]
print("Hourly keys:", list(hourly.keys()))
print("Number of hours:", len(hourly["time"]))

for i in range(3):
    print(
        hourly["time"][i],
        hourly["temperature_2m"][i],
        hourly["precipitation"][i],
        hourly["wind_speed_10m"][i],
        hourly["weather_code"][i],
    )