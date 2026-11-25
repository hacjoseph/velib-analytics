{{ config(materialized='table') }}

with snapshot as (

    select
        station_id,
        station_code,
        station_name,
        latitude,
        longitude,
        capacity,
        is_currently_listed,
        first_seen_at,
        dbt_valid_from as snapshot_valid_from,
        dbt_valid_to   as snapshot_valid_to
    from {{ ref('snap_velib__stations') }}

),

versioned as (

    select
        *,
        row_number() over (
            partition by station_id
            order by snapshot_valid_from
        ) as version_number
    from snapshot

)

select
    {{ dbt_utils.generate_surrogate_key(['station_id', 'snapshot_valid_from']) }} as station_key,
    station_id,
    station_code,
    station_name,
    latitude,
    longitude,
    capacity,
    is_currently_listed,
    {{ station_atypical_reason('station_code', 'capacity') }} as atypical_reason,
    {{ station_atypical_reason('station_code', 'capacity') }} is not null as is_atypical,
    version_number,
    -- The first known version covers all past observations,
    -- otherwise facts older than the first snapshot run would find no station.
    case
        when version_number = 1
            then least(first_seen_at, snapshot_valid_from)
        else snapshot_valid_from
    end as valid_from,
    coalesce(snapshot_valid_to, timestamp '9999-12-31') as valid_to,
    snapshot_valid_to is null as is_current
from versioned