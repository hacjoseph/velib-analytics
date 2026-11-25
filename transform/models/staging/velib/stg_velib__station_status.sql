-- Grain: one row per station per ingestion snapshot.
-- Staging rules: rename, cast, unnest. No joins, no business logic.

with source as (

    select * from {{ source('raw', 'station_status') }}

),

stations as (

    select
        source_file,
        loaded_at,
        payload ->> '$.lastUpdatedOther' as feed_last_updated_epoch,
        unnest(json_extract(payload, '$.data.stations[*]')) as station
    from source

),

renamed as (

    select
        cast(station ->> '$.station_id' as bigint)              as station_id,
        station ->> '$.stationCode'                              as station_code,

        cast(station ->> '$.num_bikes_available' as integer)    as num_bikes_available,
        coalesce(list_sum(list_transform(
            json_extract(station, '$.num_bikes_available_types[*]'),
            lambda bike_type: cast(bike_type ->> '$.mechanical' as integer)
        )), 0)                                                   as num_mechanical_bikes_available,
        coalesce(list_sum(list_transform(
            json_extract(station, '$.num_bikes_available_types[*]'),
            lambda bike_type: cast(bike_type ->> '$.ebike' as integer)
        )), 0)                                                   as num_ebikes_available,
        cast(station ->> '$.num_docks_available' as integer)    as num_docks_available,

        cast(station ->> '$.is_installed' as integer) = 1       as is_installed,
        cast(station ->> '$.is_renting' as integer) = 1         as is_renting,
        cast(station ->> '$.is_returning' as integer) = 1       as is_returning,

        {{ extract_snapshot_at('source_file') }}        as snapshot_at,
        epoch_ms(cast(station ->> '$.last_reported' as bigint) * 1000)  as last_reported_at,
        epoch_ms(cast(feed_last_updated_epoch as bigint) * 1000)       as feed_last_updated_at,

        source_file,
        loaded_at

    from stations

)

select * from renamed