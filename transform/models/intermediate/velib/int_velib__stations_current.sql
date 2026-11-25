-- Grain: one row per station (latest known version of the reference data).
-- Historical versions will be handled by a dbt snapshot (SCD2) later.
-- Atypical stations are flagged, never filtered out.

with station_versions as (

    select * from {{ ref('stg_velib__station_information') }}

),

latest_snapshot as (

    select max(snapshot_at) as latest_snapshot_at
    from station_versions

),

current_stations as (

    select
        station_id,
        station_code,
        station_name,
        latitude,
        longitude,
        capacity,
        min(snapshot_at) over (partition by station_id) as first_seen_at,
        snapshot_at                                     as last_seen_at
    from station_versions
    qualify row_number() over (
        partition by station_id
        order by snapshot_at desc, source_file desc
    ) = 1

),

flagged as (

    select
        current_stations.*,
        current_stations.last_seen_at = latest_snapshot.latest_snapshot_at
            as is_currently_listed,
        case
            when capacity = 0
                then 'zero_capacity'
            when regexp_matches(station_code, '^6[0-9]{4}$')
                then 'special_code_range'
            when capacity > {{ var('atypical_station_capacity_threshold') }}
                then 'high_capacity'
        end as atypical_reason
    from current_stations
    cross join latest_snapshot

)

select
    *,
    atypical_reason is not null as is_atypical
from flagged