-- Grain: one row per station and per status snapshot.
-- Enriches status with the current station reference (capacity, atypical flag)
-- and derives availability indicators.
-- Note: joins on the CURRENT reference; a point-in-time join on the SCD2
-- snapshot will replace this once the station snapshot exists.

with station_status as (

    select * from {{ ref('stg_velib__station_status') }}

),

stations as (

    select * from {{ ref('int_velib__stations_current') }}

),

joined as (

    select
        station_status.source_file,
        station_status.snapshot_at,
        date_trunc('hour', station_status.snapshot_at) as snapshot_hour,
        station_status.station_id,
        stations.station_code,
        stations.capacity,
        stations.is_atypical,
        station_status.num_bikes_available,
        station_status.num_mechanical_bikes_available,
        station_status.num_ebikes_available,
        station_status.num_docks_available,
        station_status.is_installed
            and station_status.is_renting
            and station_status.is_returning as is_operational
    from station_status
    left join stations
        on station_status.station_id = stations.station_id

)

select
    *,
    greatest(
        capacity - num_bikes_available - num_docks_available, 0
    ) as num_unavailable_docks,
    num_bikes_available
        / nullif(num_bikes_available + num_docks_available, 0) as fill_rate,
    case
        when not is_operational         then 'not_operational'
        when num_bikes_available = 0    then 'empty'
        when num_docks_available = 0    then 'full'
        else 'available'
    end as station_state,
    is_operational and num_bikes_available = 0 as is_empty,
    is_operational and num_docks_available = 0 as is_full
from joined