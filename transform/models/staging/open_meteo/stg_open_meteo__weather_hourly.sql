
with source as (

    select
        source_file,
        loaded_at,
        payload
    from {{ source('open_meteo', 'weather_hourly') }}

),

parsed as (

    select
        source_file,
        loaded_at,
        {{ extract_snapshot_at('source_file') }} as snapshot_at,
        from_json(
            payload -> '$.hourly',
            '{
                "time": ["VARCHAR"],
                "temperature_2m": ["DOUBLE"],
                "precipitation": ["DOUBLE"],
                "wind_speed_10m": ["DOUBLE"],
                "weather_code": ["INTEGER"]
            }'
        ) as hourly
    from source

),

unnested as (

    -- Multiple unnest calls in the same SELECT are zipped by position.
    select
        source_file,
        loaded_at,
        snapshot_at,
        unnest(hourly.time)           as weather_time_raw,
        unnest(hourly.temperature_2m) as temperature_c,
        unnest(hourly.precipitation)  as precipitation_mm,  -- sum over the preceding hour
        unnest(hourly.wind_speed_10m) as wind_speed_kmh,
        unnest(hourly.weather_code)   as weather_code       -- WMO code
    from parsed

),

typed as (

    select
        source_file,
        loaded_at,
        snapshot_at,
        strptime(weather_time_raw, '%Y-%m-%dT%H:%M') as weather_at,
        temperature_c,
        precipitation_mm,
        wind_speed_kmh,
        weather_code
    from unnested

)

select
    source_file,
    loaded_at,
    snapshot_at,
    weather_at,
    temperature_c,
    precipitation_mm,
    wind_speed_kmh,
    weather_code,
    weather_at > snapshot_at                       as is_forecast,
    date_diff('hour', snapshot_at, weather_at)     as forecast_lead_hours
from typed