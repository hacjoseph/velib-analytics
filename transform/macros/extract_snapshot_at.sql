{#
    Parse the ingestion time from a raw file name, e.g.
    raw/velib/station_status/dt=2026-11-24/station_status_20261124T174800Z.json.gz
    -> 2026-11-24 17:48:00 (naive UTC timestamp)
#}
{% macro extract_snapshot_at(file_column) -%}
    strptime(
        regexp_extract({{ file_column }}, '_(\d{8}T\d{6}Z)\.json\.gz$', 1),
        '%Y%m%dT%H%M%SZ'
    )
{%- endmacro %}