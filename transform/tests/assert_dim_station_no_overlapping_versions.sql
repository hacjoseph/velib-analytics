-- Two versions of the same station must never overlap in time.
select
    a.station_id,
    a.station_key as version_a,
    b.station_key as version_b
from {{ ref('dim_station') }} as a
inner join {{ ref('dim_station') }} as b
    on a.station_id = b.station_id
    and a.station_key < b.station_key
    and a.valid_from < b.valid_to
    and b.valid_from < a.valid_to