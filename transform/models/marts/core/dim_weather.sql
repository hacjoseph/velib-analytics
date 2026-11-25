{{ config(materialized='table') }}

{#
    Hourly weather dimension (Paris).
    Key: weather_at (naive UTC, hour start), joined on fact.snapshot_hour.
    precipitation_mm is the total of the PRECEDING hour (Open-Meteo convention).
#}

with weather as (

    select * from {{ ref('int_weather_hourly_deduplicated') }}

),

wmo as (

    select * from {{ ref('wmo_weather_codes') }}

)

select
    weather.weather_at,
    weather.temperature_c,
    weather.precipitation_mm,
    weather.wind_speed_kmh,
    weather.weather_code,
    wmo.weather_label_fr,
    wmo.weather_category,
    wmo.is_precipitation,
    weather.precipitation_mm > 0 as has_measured_precipitation,
    case
        when weather.temperature_c < 5  then 'cold'
        when weather.temperature_c < 15 then 'cool'
        when weather.temperature_c < 25 then 'mild'
        else 'hot'
    end as temperature_band,
    -- Standard rain intensity thresholds (mm/h)
    case
        when weather.precipitation_mm = 0   then 'none'
        when weather.precipitation_mm < 2.5 then 'light'
        when weather.precipitation_mm < 7.6 then 'moderate'
        else 'heavy'
    end as precipitation_band,
    weather.weather_at > weather.selected_snapshot_at as is_forecast,
    weather.selected_snapshot_at,
    weather.n_versions
from weather
left join wmo
    on weather.weather_code = wmo.weather_code