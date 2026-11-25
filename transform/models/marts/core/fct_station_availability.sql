{{ config(materialized='table') }}

{#
    Grain: one row per station and per status snapshot (~every 30 min).
    Station joined on its SCD2 version valid at snapshot time (half-open interval).
#}

with status as (

    select * from {{ ref('int_velib__station_status_enriched') }}

),

stations as (

    select station_key, station_id, valid_from, valid_to
    from {{ ref('dim_station') }}

),

weather as (

    select weather_at
    from {{ ref('dim_weather') }}
    where not is_forecast

)

select
    -- Keys
    stations.station_key,
    status.station_id,
    status.snapshot_at,
    status.snapshot_hour                  as hour_utc,
    weather.weather_at,

    -- Measures
    status.num_bikes_available,
    status.num_mechanical_bikes_available,
    status.num_ebikes_available,
    status.num_docks_available,
    status.num_unavailable_docks,
    status.fill_rate,

    -- State flags
    status.station_state,
    status.is_operational,
    status.is_empty,
    status.is_full
from status
left join stations
    on status.station_id = stations.station_id
    and status.snapshot_at >= stations.valid_from
    and status.snapshot_at < stations.valid_to
left join weather
    on status.snapshot_hour = weather.weather_at