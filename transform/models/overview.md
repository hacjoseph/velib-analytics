{% docs __overview__ %}

# Vélib' Analytics — dbt project

Availability of Vélib' bikes and docks in Paris, enriched with hourly weather.

## Layers

- **staging**: one model per source, typed and renamed, full history kept (views).
- **intermediate**: business logic: deduplication, current station reference,
  station states and fill rate (views).
- **marts**: star schema for analysis (tables).
- **snapshots**: SCD type 2 history of stations.

## Conventions

- All timestamps are **naive UTC**. Paris local time only appears in `dim_time`.
- Facts join dimensions on surrogate keys; SCD2 validity is half-open
  (`valid_from <= t < valid_to`).
- Atypical stations are **flagged, never filtered**.

{% enddocs %}