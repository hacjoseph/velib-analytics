-- Grain: one row per hour (weather_at).
-- Rule: for each hour, keep the version from the most recent API call.
-- For past hours this yields a past (non-forecast) value whenever one exists;
-- for future hours, the freshest forecast.

with weather_versions as (

    select * from {{ ref('stg_open_meteo__weather_hourly') }}

)

select
    weather_at,
    temperature_c,
    precipitation_mm,
    wind_speed_kmh,
    weather_code,
    is_forecast,
    snapshot_at                                      as selected_snapshot_at,
    source_file                                      as selected_source_file,
    count(*) over (partition by weather_at)          as n_versions
from weather_versions
qualify row_number() over (
    partition by weather_at
    order by snapshot_at desc, source_file desc
) = 1