{% docs snapshot_at %}
Time of the GBFS snapshot, taken from the `lastUpdatedOther` field of the file,
in naive UTC. One snapshot is collected about every 30 minutes.
{% enddocs %}

{% docs hour_utc_convention %}
Hour start in naive UTC. This is the join key between the fact table,
`dim_time` and `dim_weather`. Convert to Europe/Paris only through `dim_time`.
{% enddocs %}

{% docs station_key %}
Surrogate key of a station **version** (SCD type 2), computed from
`station_id` and the start of validity. Facts must join on this key,
not on `station_id`.
{% enddocs %}