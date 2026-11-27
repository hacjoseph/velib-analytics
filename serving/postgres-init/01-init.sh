#!/usr/bin/env bash
# Runs once, on the first start of the container (empty data volume).
# Creates least-privilege roles, the analytics schema and Metabase's app database.
set -euo pipefail

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v writer_password="$ANALYTICS_WRITER_PASSWORD" \
  -v reader_password="$METABASE_READER_PASSWORD" \
  -v metabase_password="$METABASE_DB_PASSWORD" <<'SQL'
-- Publisher (Airflow task): owns and rewrites the analytics tables
CREATE ROLE analytics_writer LOGIN PASSWORD :'writer_password';
-- BI tool: read-only access to analytics
CREATE ROLE metabase_reader LOGIN PASSWORD :'reader_password';
-- Metabase application database owner (questions, dashboards, users)
CREATE ROLE metabase LOGIN PASSWORD :'metabase_password';

CREATE SCHEMA analytics AUTHORIZATION analytics_writer;
GRANT USAGE ON SCHEMA analytics TO metabase_reader;
-- Tables created later by analytics_writer are automatically readable by Metabase
ALTER DEFAULT PRIVILEGES FOR ROLE analytics_writer IN SCHEMA analytics
  GRANT SELECT ON TABLES TO metabase_reader;

CREATE DATABASE metabase OWNER metabase;
SQL