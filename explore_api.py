import requests

URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"

response = requests.get(URL, timeout=10)
print("HTTPstatus: ", response.status_code)

payload = response.json()
print("top-level keys: ", payload.keys())

stations = payload["data"]["stations"]
print("Number of stations: ", len(stations))
print("First station: ", stations[0])