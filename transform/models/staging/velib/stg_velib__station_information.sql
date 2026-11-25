-- Grain: one row per station per ingestion snapshot.
-- Full history is kept on purpose: the station dimension (SCD2) will be built
-- from it later with a dbt snapshot.

with source as (

    select * from {{ source('raw', 'station_information') }}

),

stations as (

    select
        source_file,
        loaded_at,
        unnest(json_extract(payload, '$.data.stations[*]')) as station
    from source

),

renamed as (

    select
        cast(station ->> '$.station_id' as bigint)      as station_id,
        station ->> '$.stationCode'                      as station_code,

        trim(station ->> '$.name')                       as station_name,
        cast(station ->> '$.lat' as double)              as latitude,
        cast(station ->> '$.lon' as double)              as longitude,
        cast(station ->> '$.capacity' as integer)        as capacity,

        {{ extract_snapshot_at('source_file') }}         as snapshot_at,

        source_file,
        loaded_at

    from stations

)

select * from renamed