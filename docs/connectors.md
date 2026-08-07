# Connector guide

Connector definitions live in `config/sources.yml` locally and
`config/sources.aws.yml` on AWS. Only enabled definitions become Dagster
assets. Environment substitutions use `${UPPER_CASE_NAME}` and fail closed
when a variable required by an enabled source is missing. Disabled examples do
not require their secrets to exist.

After changing source definitions, restart `platform-code`,
`dagster-webserver`, and `dagster-daemon` so Dagster reloads the asset graph.

## Filesystem and S3

One filesystem source can expose several files as separate dlt resources:

```yaml
- name: finance_files
  type: filesystem
  enabled: true
  dataset: raw_finance
  bucket_url: /opt/data-platform/data/finance
  tables:
    - name: accounts
      file_glob: accounts-*.csv
      format: csv
    - name: transactions
      file_glob: transactions-*.parquet
      format: parquet
    - name: adjustments
      file_glob: adjustments.json
      format: json
      records_path: response.items
```

`json` accepts either one object or an array of objects. `records_path` selects
a dot-separated object path before records are yielded. Use `jsonl` for
newline-delimited JSON.

Change `bucket_url` to `s3://bucket/prefix` for AWS. On EC2, omit credentials
to use the instance role. For local MinIO:

```yaml
credentials:
  aws_access_key_id: ${AWS_ACCESS_KEY_ID}
  aws_secret_access_key: ${AWS_SECRET_ACCESS_KEY}
  endpoint_url: ${S3_ENDPOINT_URL}
```

`config/sources.demo-minio.yml` is a ready-to-run MinIO ingestion example.

CSV uses dlt's DuckDB reader; Parquet uses PyArrow. Both stream in chunks
instead of loading a whole file into Python objects.

## PostgreSQL and MySQL

The database connector uses SQLAlchemy URLs and dlt's `sql_database` source.
The URL itself stays out of YAML:

```yaml
- name: crm
  type: database
  enabled: true
  engine: mysql
  credentials_env: CRM_MYSQL_URL
  table_names: [contacts, companies]
  backend: pyarrow
  chunk_size: 50000
```

Supported engine values are `postgresql` and `mysql`. `backend` may use a dlt
SQL source backend; `pyarrow` is the platform default because it preserves
source types and transfers batches efficiently.

Network access is separate from connector configuration. AWS sources in a
private VPC or on premises need VPC peering, Transit Gateway, VPN, or another
explicit route and matching security rules.

## REST APIs

The connector passes its `client`, pagination, authentication, and resources
to dlt's REST API source. Common patterns include:

```yaml
auth:
  type: bearer
  token: ${API_TOKEN}
paginator:
  type: json_link
  next_url_path: paging.next
resources:
  - name: records
    endpoint:
      path: records
      params:
        status: active
```

Use dlt's REST API configuration vocabulary for endpoint dependencies,
incremental cursor parameters, response selectors, and other pagination
strategies. `config/sources.demo-api.yml` provides a public, token-free smoke
test.

## Add another connector type

Create a subclass in `src/data_platform/connectors/`:

```python
from data_platform.connectors.base import BaseConnector


class ExampleConnector(BaseConnector):
    connector_type = "example"

    def build_source(self):
        # Return a dlt source, resource, or list of resources.
        ...
```

Import it from `src/data_platform/connectors/__init__.py`, add tests, and use
`type: example` in YAML. Registration happens through `connector_type`; the
Dagster asset factory and ClickHouse destination do not need to change.
