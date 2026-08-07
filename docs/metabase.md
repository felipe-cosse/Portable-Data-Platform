# Metabase operations guide

Metabase is the optional business-intelligence layer for Portable Data
Platform. It reads dbt models and analytical marts from ClickHouse without
becoming part of the ingestion or transformation critical path.

## Architecture

The `bi` Docker Compose profile adds three components:

- `metabase` serves the web application on loopback port `3001`.
- `metabase-postgres` persists users, permissions, questions, and dashboards.
- `metabase-clickhouse-init` creates or rotates a dedicated read-only
  ClickHouse account, then exits.

Metabase's application database and the analytical warehouse are deliberately
separate. PostgreSQL stores Metabase metadata; ClickHouse remains the source of
analytical data.

## Start locally

Copy the environment template if the platform has not been bootstrapped:

```bash
make bootstrap
```

`make bootstrap` generates a private `METABASE_ENCRYPTION_SECRET_KEY` in the
ignored `.env` file when one is missing. Never copy that generated value into
`.env.example`, Compose configuration, documentation, or another tracked file.
Replace the remaining Metabase password placeholders in `.env`, then start the
BI profile:

```bash
make bi-up
```

Follow startup logs when needed:

```bash
make bi-logs
```

Metabase performs application-database migrations on first boot, so the first
healthy start can take longer than subsequent starts. Open
<http://localhost:3001> and create the initial administrator.

## Connect ClickHouse

In **Admin settings → Databases → Add a database**, select ClickHouse and use:

| Setting | Value |
|---|---|
| Display name | `ClickHouse analytics` |
| Host | `clickhouse` |
| Port | `8123` |
| Database name | Value of `CLICKHOUSE_DB` (`analytics` by default) |
| Username | Value of `METABASE_CLICKHOUSE_USER` |
| Password | Value of `METABASE_CLICKHOUSE_PASSWORD` |
| Use a secure connection | Off for the internal Compose network |

The initialization container grants only `SELECT` on the configured ClickHouse
database. Keep transformations in dbt and expose curated marts to dashboard
authors rather than granting Metabase write access.

## Provision the starter dashboard

The repository includes an idempotent API provisioner. Add the existing
Metabase administrator credentials to the ignored `.env` file:

```dotenv
METABASE_ADMIN_EMAIL=admin@example.com
METABASE_ADMIN_PASSWORD=replace-with-the-existing-password
```

Then run:

```bash
make metabase-provision
```

The password is used only to obtain an in-memory Metabase session. The command
does not print the password or session and does not write either value back to
disk.

The provisioner safely creates or updates:

- The `ClickHouse Analytics` connection using the dedicated read-only user.
- A `Portable Data Platform` collection.
- Four headline questions: total customers, active customers, total orders,
  and lifetime value.
- Segment charts for lifetime value and order/event activity.
- A customer-detail table with order and activity timestamps.
- A `Customer Overview` dashboard with one segment filter across every card.

All seven questions query the durable dbt `analytics.customer_activity` mart.
The command executes each question and verifies the final dashboard card count
before printing its URL. Running it again updates the existing objects instead
of creating duplicates.

## Deploy on AWS

Set the following values in `terraform/terraform.tfvars`:

```hcl
enable_metabase = true
instance_type   = "t4g.large"
```

The Terraform example enables Metabase on an Arm-based instance with 8 GiB of
memory. Terraform generates the PostgreSQL password, ClickHouse read-only
password, and encryption key, then stores them in the platform Secrets Manager
secret.

AWS security groups expose no inbound ports. After deployment, forward
Metabase through Systems Manager:

```bash
$(terraform output -raw metabase_port_forward_command)
```

Then open <http://localhost:3001>. Use the same internal ClickHouse settings as
the local deployment.

To run the provisioner from an SSM shell after setting the admin variables in
`/opt/data-platform/.env`:

```bash
cd /opt/data-platform
sudo docker compose --env-file .env --profile bi run --rm \
  -e METABASE_URL=http://metabase:3000 \
  platform-code \
  python -m data_platform.metabase_provision --env-file /dev/null
```

## Security checklist

- Replace every local `CHANGE_ME` value before using real data.
- Keep `METABASE_ENCRYPTION_SECRET_KEY` stable and backed up securely. Losing
  it prevents Metabase from decrypting stored connection details.
- Never place a generated encryption key in `.env.example` or
  `docker-compose.yml`; `make bootstrap` stores it only in ignored `.env`.
- Use the generated `metabase` ClickHouse account, not the platform ingestion
  account.
- Give Metabase groups access only to the databases, schemas, and collections
  they need.
- Do not enable public links for confidential dashboards.
- Add TLS and an authenticated reverse proxy before exposing Metabase beyond
  loopback or SSM forwarding.
- Restrict access to Terraform state because it contains generated passwords.

## Persistence and backup

The `metabase-postgres-data` volume contains Metabase application state.
Removing containers does not delete it, but `docker compose down --volumes`
does.

Back up both systems on a schedule:

- PostgreSQL application database: `pg_dump` plus a tested restore.
- ClickHouse analytical data: ClickHouse backups plus a tested restore.
- Encryption key: a protected secrets backup independent of the database
  backup.

On the single-node AWS deployment, both Docker volumes live on the encrypted
root EBS volume and do not survive instance replacement unless restored from a
backup.

## Operations

Check profile status:

```bash
docker compose --env-file .env --profile bi ps
```

Check the Metabase health endpoint:

```bash
make bi-smoke
```

Verify the ClickHouse grant:

```bash
docker compose --env-file .env exec clickhouse \
  sh -c 'clickhouse-client \
    --user "$CLICKHOUSE_USER" \
    --password "$CLICKHOUSE_PASSWORD" \
    --query "SHOW GRANTS FOR metabase"'
```

When rotating `METABASE_CLICKHOUSE_PASSWORD`, update `.env` and rerun:

```bash
docker compose --env-file .env --profile bi up \
  --force-recreate metabase-clickhouse-init
```

Then update the saved ClickHouse password in Metabase. Do not rotate
`METABASE_ENCRYPTION_SECRET_KEY` as a normal password change; follow Metabase's
encryption-key rotation procedure so saved connection details remain usable.

## Official references

- [Running Metabase on Docker](https://www.metabase.com/docs/latest/installation-and-operation/running-metabase-on-docker)
- [Connecting Metabase to ClickHouse](https://www.metabase.com/docs/latest/databases/connections/clickhouse)
- [Database users, roles, and privileges](https://www.metabase.com/docs/latest/databases/users-roles-privileges)
- [Encrypting database details at rest](https://www.metabase.com/docs/latest/databases/encrypting-details-at-rest)
