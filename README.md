<p align="center">
  <img
    src="docs/assets/portable-data-platform-hero.webp"
    alt="Portable data platform connecting files, databases, object storage, orchestration, and analytics"
    width="100%"
  />
</p>

<h1 align="center">Portable Data Platform</h1>

<p align="center">
  A compact, source-agnostic analytics platform for local development and AWS.<br />
  Ingest with dlt, orchestrate with Dagster, store in ClickHouse, transform with dbt,
  and explore files with DuckDB.
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white" alt="Python 3.11 through 3.14" />
  </a>
  <a href="https://docs.docker.com/compose/">
    <img src="https://img.shields.io/badge/Docker_Compose-local-2496ED?logo=docker&logoColor=white" alt="Docker Compose" />
  </a>
  <a href="https://developer.hashicorp.com/terraform">
    <img src="https://img.shields.io/badge/Terraform-AWS-844FBA?logo=terraform&logoColor=white" alt="Terraform on AWS" />
  </a>
  <a href="https://dagster.io/">
    <img src="https://img.shields.io/badge/orchestration-Dagster-4F43DD" alt="Dagster orchestration" />
  </a>
  <a href="https://clickhouse.com/">
    <img src="https://img.shields.io/badge/warehouse-ClickHouse-FFCC01?logo=clickhouse&logoColor=black" alt="ClickHouse warehouse" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-D22128?logo=apache&logoColor=white" alt="Apache License 2.0" />
  </a>
</p>

Portable Data Platform is a complete reference implementation for teams that
need reliable analytics without starting with Kubernetes or a managed cloud
warehouse. The same application bundle runs on a laptop through Docker Compose
and on AWS through Terraform.

It is designed around replaceable boundaries: sources are declared in YAML,
connectors register through a small Python interface, orchestration is
asset-based, and infrastructure concerns stay outside transformation logic.

## Why this project?

Small teams often accumulate operational data across spreadsheets, application
databases, third-party APIs, object storage, and exported files. Answering a
cross-system question then becomes a manual reconciliation exercise.

This project provides a practical path from those disconnected systems to
tested analytical models:

- **Configuration-first ingestion** for files, databases, S3, MinIO, and APIs.
- **Asset-based orchestration** with lineage, schedules, retries, and run history.
- **Columnar analytical storage** without requiring a managed warehouse.
- **Version-controlled SQL transformations** and data-quality tests.
- **Identical application topology** for local Docker and AWS.
- **Embedded file analytics** with DuckDB—no additional server required.
- **No public AWS ingress**; operational access uses Systems Manager.

## Architecture

```mermaid
flowchart LR
    subgraph Sources["Data sources"]
        Files["CSV · JSON · JSONL · Parquet"]
        Databases["PostgreSQL · MySQL"]
        ObjectStorage["S3 · MinIO"]
        APIs["REST APIs"]
    end

    subgraph Control["Control plane"]
        Dagster["Dagster assets<br/>schedules · lineage · runs"]
        Dlt["dlt connector layer<br/>schema · state · loading"]
    end

    subgraph Analytics["Analytics plane"]
        ClickHouse["ClickHouse<br/>analytical storage"]
        Dbt["dbt<br/>models · tests"]
        Marts["Analytics marts"]
    end

    DuckDB["DuckDB<br/>embedded file queries"]

    Files --> Dlt
    Databases --> Dlt
    ObjectStorage --> Dlt
    APIs --> Dlt
    Dagster --> Dlt
    Dlt --> ClickHouse
    ClickHouse --> Dbt
    Dbt --> Marts
    Files -. "direct query" .-> DuckDB
    ObjectStorage -. "direct query" .-> DuckDB
```

Dagster creates one ingestion asset for every enabled source. dlt performs
extraction, schema inference, normalization, pipeline-state management, and
loading. dbt builds tested staging models and marts in ClickHouse. DuckDB is
used for lightweight local and S3 exploration.

## Technology stack

| Concern | Technology | Responsibility |
|---|---|---|
| Orchestration | [Dagster](https://dagster.io/) | Assets, schedules, lineage, retries, run history |
| Ingestion | [dlt](https://dlthub.com/) | Extraction, normalization, schema evolution, loading state |
| Warehouse | [ClickHouse](https://clickhouse.com/) | Columnar analytical storage and query execution |
| Transformation | [dbt](https://www.getdbt.com/) | SQL models, dependencies, documentation, data tests |
| File analytics | [DuckDB](https://duckdb.org/) | Embedded CSV, JSON, Parquet, and S3 queries |
| Local runtime | [Docker Compose](https://docs.docker.com/compose/) | Reproducible multi-service development environment |
| Cloud infrastructure | [Terraform](https://developer.hashicorp.com/terraform) | AWS networking, compute, storage, IAM, and secrets |
| Local object storage | [MinIO](https://min.io/) | S3-compatible development and integration testing |

## Supported connectivity

| Source | Formats or protocol | Configuration |
|---|---|---|
| Local filesystem | CSV, JSON, JSONL, Parquet | File globs and table names in YAML |
| Amazon S3 | CSV, JSON, JSONL, Parquet | IAM role in AWS; no static cloud keys required |
| MinIO | CSV, JSON, JSONL, Parquet | S3-compatible endpoint for local integration |
| PostgreSQL | SQLAlchemy / psycopg2 | Secret URL supplied through an environment variable |
| MySQL | SQLAlchemy / PyMySQL | Secret URL supplied through an environment variable |
| REST APIs | HTTP, bearer auth, pagination | Declarative dlt REST configuration |

New connector types can be added without changing the Dagster asset factory.
See the [connector guide](docs/connectors.md) for supported options and the
extension interface.

## Quick start

### Prerequisites

- Docker Engine or Docker Desktop with Compose
- GNU Make
- Approximately 4 GB of available Docker memory for the complete demo

### Start the platform

```bash
git clone <your-repository-url>
cd data-platform
make up
```

`make up` performs the complete local bootstrap:

1. Copies `.env.example` to `.env` when needed.
2. Builds the shared Python runtime.
3. Generates a real Parquet demonstration file.
4. Starts ClickHouse, Dagster, Dagster's PostgreSQL metadata database, and MinIO.

> [!IMPORTANT]
> Replace every `CHANGE_ME` value in `.env` before connecting non-demo data.
> Published ports bind to `127.0.0.1`, so they are not exposed to the local
> network by default.

### Open the services

| Service | URL | Purpose |
|---|---|---|
| Dagster | <http://localhost:3000> | Assets, runs, schedules, lineage, logs |
| ClickHouse HTTP | <http://localhost:8123> | Warehouse HTTP endpoint |
| MinIO console | <http://localhost:9001> | Local S3-compatible storage |

### Run the example pipeline

```bash
# Ingest the sample CSV, JSON, and Parquet assets.
make ingest

# Build the dbt staging models and analytical mart.
make dbt-build

# Query the sample files directly through embedded DuckDB.
make query
```

The bundled example materializes:

- `customers.csv`
- `events.json`
- `orders.parquet`
- Three dbt staging views
- A tested `customer_activity` analytical mart

### Useful commands

| Command | Action |
|---|---|
| `make up` | Build and start the standard local platform |
| `make demo-up` | Also start seeded PostgreSQL and MySQL source systems |
| `make ps` | Show platform service status |
| `make logs` | Follow service logs |
| `make ingest` | Materialize all enabled ingestion assets |
| `make dbt-build` | Build and test the dbt project |
| `make query` | Run the bundled DuckDB example |
| `make test` | Run the Python test suite in the platform image |
| `make down` | Stop the complete local environment |

## Configure a source

Source definitions live in [`config/sources.yml`](config/sources.yml). Only
enabled definitions become Dagster assets.

The following source reads three formats from one S3 prefix:

```yaml
version: 1

sources:
  - name: product_data
    type: filesystem
    enabled: true
    dataset: raw_product_data
    write_disposition: append
    bucket_url: s3://${DATA_LAKE_BUCKET}/landing
    tables:
      - name: customers
        file_glob: customers/**/*.csv
        format: csv
      - name: events
        file_glob: events/**/*.jsonl
        format: jsonl
      - name: orders
        file_glob: orders/**/*.parquet
        format: parquet
```

Environment substitutions use `${UPPER_CASE_NAME}` and fail closed when an
enabled source requires a missing value. Disabled examples do not require their
secrets.

After changing source definitions, restart the Dagster code location and
services:

```bash
docker compose --env-file .env restart \
  platform-code dagster-webserver dagster-daemon
```

### Database source

Database credentials remain outside YAML:

```yaml
- name: application_db
  type: database
  enabled: true
  dataset: raw_application
  write_disposition: replace
  engine: postgresql
  credentials_env: SOURCE_POSTGRES_URL
  schema: public
  table_names: [users, subscriptions]
  backend: pyarrow
```

Set `SOURCE_POSTGRES_URL` to a SQLAlchemy URL such as
`postgresql+psycopg2://user:password@host:5432/database`. MySQL uses
`mysql+pymysql://...`.

### REST API source

API resources, authentication, parameters, and pagination are declarative:

```yaml
- name: billing_api
  type: api
  enabled: true
  dataset: raw_billing
  base_url: https://api.example.com/v1/
  auth:
    type: bearer
    token: ${BILLING_API_TOKEN}
  paginator:
    type: json_link
    next_url_path: paging.next
  resources:
    - name: invoices
      endpoint:
        path: invoices
```

See [`config/sources.demo-api.yml`](config/sources.demo-api.yml) for a public,
token-free API example.

## Query files with DuckDB

The DuckDB CLI registers the input as a view named `source`:

```bash
docker compose --env-file .env run --rm platform-code \
  python -m data_platform.duckdb_cli \
  /opt/data-platform/data/inbox/orders.parquet \
  --sql "select customer_id, sum(amount) from source group by customer_id"
```

The same command accepts `s3://bucket/path/*.parquet`. It configures DuckDB's
S3 support from the AWS credential chain or the local MinIO environment.

DuckDB is intentionally embedded rather than deployed as another service. It
is ideal for development, file inspection, and pipeline validation; ClickHouse
remains the persistent analytical warehouse.

## Run the database and object-storage demos

Start the seeded PostgreSQL and MySQL systems:

```bash
make demo-up
```

To exercise both database connectors without editing the main configuration:

```bash
docker compose --env-file .env --profile demo run --rm \
  -e SOURCE_CONFIG_PATH=/opt/data-platform/config/sources.demo-databases.yml \
  platform-code \
  dagster asset materialize --select 'group:ingestion' \
  -m data_platform.definitions
```

Additional ready-to-run configurations:

- [`config/sources.demo-databases.yml`](config/sources.demo-databases.yml)
- [`config/sources.demo-minio.yml`](config/sources.demo-minio.yml)
- [`config/sources.demo-api.yml`](config/sources.demo-api.yml)

## Deploy to AWS

The Terraform stack provisions a secure, economical single-node deployment:

- Amazon Linux 2023 EC2, Graviton by default
- Encrypted gp3 root volume
- Dedicated VPC, public subnet, and internet gateway for outbound bootstrap
- No inbound security-group rules
- Systems Manager access instead of SSH
- Private, encrypted, versioned S3 data-lake and artifact bucket
- Least-privilege instance role for SSM, S3, and one runtime secret
- Generated service credentials in AWS Secrets Manager

### Deploy

```bash
make bundle-ready

cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Terraform outputs commands for secure access:

```bash
# Keyless shell access.
$(terraform output -raw start_session_command)

# Forward Dagster without opening an inbound port.
$(terraform output -raw dagster_port_forward_command)
```

Run the port-forward command, then open <http://localhost:3000>.

See the [AWS deployment guide](terraform/README.md) for first-boot diagnostics,
application updates, S3 ingestion, remote-state guidance, backups, and safe
destruction.

## Local and AWS parity

| Capability | Local | AWS |
|---|---|---|
| Application topology | Docker Compose | The same Docker Compose bundle |
| Orchestration | Dagster | Dagster |
| Warehouse | ClickHouse volume | ClickHouse on encrypted EBS |
| Object storage | MinIO | Private, versioned S3 |
| Runtime secrets | Local `.env` | Secrets Manager fetched at first boot |
| Cloud credentials | Optional local values | EC2 instance role |
| Administrative access | Loopback ports | Systems Manager and port forwarding |
| Infrastructure | Make and Compose | Terraform |

## Security model

- Every published local port binds to `127.0.0.1`.
- AWS has no inbound security-group rules.
- EC2 requires IMDSv2 with a hop limit that supports containers.
- AWS credentials come from the instance role, never Terraform user data.
- Runtime service credentials are retrieved from Secrets Manager.
- EBS and S3 are encrypted.
- S3 public access is blocked and versioning is enabled.
- The Terraform bucket defaults to `force_destroy = false`.
- T-family instances default to standard CPU credits to avoid surprise
  surplus-credit charges.

> [!CAUTION]
> Terraform state contains generated passwords because Terraform creates the
> Secrets Manager value. Configure an encrypted remote backend and tightly
> control state access before team or production use.

## Warehouse strategy

ClickHouse is the implemented and fully tested warehouse backend. It fits the
current append-oriented, low-operations, single-node design and has a
first-party dlt destination.

StarRocks can be added later as a complementary analytical backend for
primary-key updates, CDC, join-heavy BI workloads, or lakehouse catalogs. The
recommended dual-warehouse design is to land canonical Parquet in S3 or MinIO
once, then create separate Dagster assets and dbt targets for each warehouse.
StarRocks is **not included in the current Compose or Terraform deployment**.

## Project structure

```text
.
├── config/                 # Local, AWS, and integration source definitions
├── dagster/                # Dagster instance and workspace configuration
├── data/inbox/             # CSV, JSON, and generated Parquet examples
├── dbt/                    # ClickHouse models, sources, tests, and profiles
├── docs/                   # Connector and deployment documentation
├── infra/                  # MinIO and seeded database initialization
├── scripts/                # Demo generation, validation, and smoke tests
├── src/data_platform/      # Connector registry, Dagster assets, DuckDB CLI
├── terraform/              # Complete AWS infrastructure and bootstrap
├── tests/                  # Configuration, connector, and query tests
├── docker-compose.yml
├── Dockerfile
└── Makefile
```

## Validation

The reference implementation has been exercised across the complete local
path:

- 13 Python tests
- Ruff static analysis
- CSV, JSON, and Parquet ingestion through Dagster and dlt
- PostgreSQL and MySQL integration sources
- MinIO/S3-compatible Parquet ingestion
- Declarative REST API ingestion
- 10 successful dbt models and tests
- DuckDB file queries
- Docker Compose health and smoke checks
- Terraform formatting and validation

Run the repeatable checks:

```bash
make test

python3 -m pip install -r requirements-dev.txt
make lint

make validate
make terraform-validate
sh scripts/smoke_test.sh
```

## Production boundaries

This repository is a production-minded reference implementation, not a
high-availability cluster.

Before storing business-critical data, add:

- Automated ClickHouse backups and tested restores
- CloudWatch or Prometheus monitoring and alerting
- TLS through an authenticated proxy or load balancer
- Recovery objectives and incident procedures
- Separate environments and failure domains
- CI checks for tests, linting, dbt, Compose, and Terraform plans
- A remote encrypted Terraform backend with state locking

The default EC2 instance is intended for demonstration and light workloads.
Benchmark representative ingestion, transformations, query concurrency, and
retention before selecting production infrastructure.

The `$20/month` claim that inspired the project is not a cost guarantee. EC2,
EBS, public IPv4, Secrets Manager, S3, data transfer, backups, and regional
pricing all contribute to the actual bill.

## Roadmap

- [ ] Optional StarRocks backend through a shared S3/MinIO Parquet layer
- [ ] CDC ingestion for PostgreSQL and MySQL
- [ ] Automated ClickHouse backups and restore verification
- [ ] Metrics, dashboards, and alerting
- [ ] GitHub Actions validation workflow
- [ ] Optional semantic or BI serving layer

## Contributing

Contributions are welcome:

1. Fork the repository and create a focused branch.
2. Add tests for behavioral changes.
3. Run the validation commands above.
4. Update connector or deployment documentation when interfaces change.
5. Open a pull request explaining the problem, design, and verification.

Please avoid committing `.env`, Terraform state, cloud credentials, database
URLs, or generated runtime data.

## License

Licensed under the [Apache License 2.0](LICENSE).

Copyright 2026 The Portable Data Platform Authors.

---

<p align="center">
  Built for teams that want a capable data platform before they need a platform team.
</p>
