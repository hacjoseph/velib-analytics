{#
    Returns the first matching reason why a station is atypical, or null.
    Rule order matters: the first matching reason wins.
    Stations are flagged, never filtered out.
#}
{% macro station_atypical_reason(station_code, capacity) %}
    case
        when {{ capacity }} = 0
            then 'zero_capacity'
        when regexp_matches(cast({{ station_code }} as varchar), '^6[0-9]{4}$')
            then 'special_code_range'
        when {{ capacity }} > {{ var('atypical_station_capacity_threshold') }}
            then 'high_capacity'
    end
{% endmacro %}