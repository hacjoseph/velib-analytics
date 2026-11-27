# syntax=docker/dockerfile:1
FROM apache/airflow:3.3.1

ENV VELIB_HOME=/opt/velib \
    VELIB_VENV=/opt/velib-venv

USER root

# Pipeline dependencies live in their own virtualenv, isolated from Airflow's.
# Requirements are copied first so this layer stays cached when code changes.
# COPY loading/requirements.txt /tmp/requirements/loading.txt
COPY requirements.txt /tmp/requirements/ingestion-loading.txt
COPY transform/requirements.txt /tmp/requirements/transform.txt
RUN python -m venv "${VELIB_VENV}" \
    && "${VELIB_VENV}/bin/pip" install --no-cache-dir --upgrade pip \
    && "${VELIB_VENV}/bin/pip" install --no-cache-dir \
        -r /tmp/requirements/ingestion-loading.txt \
        -r /tmp/requirements/transform.txt \
    && rm -rf /tmp/requirements

COPY serving/requirements.txt /tmp/requirements/serving.txt
# ... in the pip install command, add:
#        -r /tmp/requirements/serving.txt \
# ... and after the other COPY lines:
COPY serving ${VELIB_HOME}/serving

COPY ingestion ${VELIB_HOME}/ingestion
COPY loading ${VELIB_HOME}/loading

USER airflow