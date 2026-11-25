{{ config(materialized='table') }}

{#
    Hourly time dimension.
    Key: hour_utc (naive UTC timestamp, same convention as snapshot_hour and weather_at).
    Analysis attributes: Europe/Paris local time, because rider behaviour
    follows the local clock (rush hours do not move with daylight saving time).
#}

with spine as (

    {{ dbt_utils.date_spine(
        datepart="hour",
        start_date="cast('" ~ var('dim_time_start_date') ~ "' as timestamp)",
        end_date="cast('" ~ var('dim_time_end_date') ~ "' as timestamp)"
    ) }}

),

hours as (

    select
        cast(date_hour as timestamp) as hour_utc,
        -- naive UTC -> timestamptz (interpreted as UTC) -> naive Paris local time
        timezone('Europe/Paris', timezone('UTC', cast(date_hour as timestamp))) as local_at
    from spine

)

select
    hour_utc,
    local_at,
    cast(local_at as date)              as local_date,
    extract('hour' from local_at)       as local_hour,
    extract('isodow' from local_at)     as iso_day_of_week,   -- 1 = Monday, 7 = Sunday
    case extract('isodow' from local_at)
        when 1 then 'lundi'
        when 2 then 'mardi'
        when 3 then 'mercredi'
        when 4 then 'jeudi'
        when 5 then 'vendredi'
        when 6 then 'samedi'
        when 7 then 'dimanche'
    end                                 as day_name_fr,
    extract('isodow' from local_at) in (6, 7) as is_weekend,
    extract('week' from local_at)       as iso_week,
    extract('month' from local_at)      as month,
    extract('year' from local_at)       as year,
    case
        when extract('hour' from local_at) between 0 and 5   then 'night'
        when extract('hour' from local_at) between 6 and 9   then 'morning_peak'
        when extract('hour' from local_at) between 10 and 15 then 'daytime'
        when extract('hour' from local_at) between 16 and 19 then 'evening_peak'
        else 'evening'
    end                                 as time_slot
from hours