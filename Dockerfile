FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DAGSTER_HOME=/opt/data-platform/dagster

WORKDIR /opt/data-platform

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src ./src
RUN pip install --no-deps .

COPY config ./config
COPY dagster ./dagster
COPY dbt ./dbt
COPY scripts ./scripts
COPY tests ./tests
COPY data ./data

RUN mkdir -p /opt/dagster/dlt /opt/dagster/duckdb \
    && chmod +x scripts/*.sh

CMD ["dagster", "api", "grpc", "-m", "data_platform.definitions", "-h", "0.0.0.0", "-p", "4000"]
