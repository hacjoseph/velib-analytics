import os

import duckdb

STATUS_FILES = "s3://velib-raw/raw/velib/station_status/*/*.json.gz"
INFO_FILES = "s3://velib-raw/raw/velib/station_information/*/*.json.gz"

con = duckdb.connect()  # in-memory database, nothing written to disk

con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"""
    CREATE SECRET velib_s3 (
        TYPE s3,
        KEY_ID '{os.environ["OBJECT_STORAGE_ACCESS_KEY"]}',
        SECRET '{os.environ["OBJECT_STORAGE_SECRET_KEY"]}',
        ENDPOINT 'localhost:9000',
        URL_STYLE 'path',
        USE_SSL false,
        REGION 'us-east-1'
    )
""")

print("1. Snapshots collected per day")
con.sql(f"""
    SELECT
        dt,
        count(*) AS snapshots,
        min(to_timestamp(lastUpdatedOther)) AS first_snapshot,
        max(to_timestamp(lastUpdatedOther)) AS last_snapshot
    FROM read_json('{STATUS_FILES}', hive_partitioning = true)
    GROUP BY dt
    ORDER BY dt
""").show()

print("2. Empty and full stations in the latest snapshot")
con.sql(f"""
    WITH latest AS (
        SELECT data
        FROM read_json('{STATUS_FILES}', filename = true)
        ORDER BY filename DESC
        LIMIT 1
    ),
    stations AS (
        SELECT unnest(data.stations) AS s
        FROM latest
    )
    SELECT
        count(*) AS stations_in_service,
        count(*) FILTER (WHERE s.num_bikes_available = 0) AS empty_stations,
        count(*) FILTER (WHERE s.num_docks_available = 0) AS full_stations
    FROM stations
    WHERE s.is_installed = 1
""").show()

print("3. Biggest empty stations right now")
con.sql(f"""
    WITH latest_status AS (
        SELECT unnest(data.stations) AS s
        FROM (
            SELECT data FROM read_json('{STATUS_FILES}', filename = true)
            ORDER BY filename DESC LIMIT 1
        )
    ),
    latest_info AS (
        SELECT unnest(data.stations) AS i
        FROM (
            SELECT data FROM read_json('{INFO_FILES}', filename = true)
            ORDER BY filename DESC LIMIT 1
        )
    )
    SELECT
        i.name,
        i.capacity,
        s.num_bikes_available,
        s.num_docks_available
    FROM latest_status
    JOIN latest_info ON s.station_id = i.station_id
    WHERE s.is_installed = 1
      AND s.num_bikes_available = 0
    ORDER BY i.capacity DESC
    LIMIT 10
""").show()