# AWS deployment

This Terraform stack deploys the same Docker Compose platform used locally to
one Amazon Linux 2023 EC2 instance. It is intentionally a small-team,
single-node design.

## Prerequisites

- Terraform 1.5.7 or later
- AWS credentials able to create VPC, EC2, IAM, S3, Secrets Manager, and SSM
  resources
- Docker, used by `make bundle-ready` to generate the demo Parquet file
- Session Manager plugin for AWS CLI port forwarding

From the repository root:

```bash
make bundle-ready
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

The example variables enable Metabase on `t4g.large`. For the lower-cost core
stack without BI, set `enable_metabase = false` and
`instance_type = "t4g.medium"`.

Set the choice before the first apply. The instance deliberately does not
replace itself when user data changes, because replacement would also replace
the root-volume data. To enable Metabase on an existing instance, open an SSM
shell and add a systemd override:

```ini
[Service]
Environment="COMPOSE_PROFILES=bi"
```

Run `sudo systemctl edit data-platform`, save the override, then run
`sudo systemctl daemon-reload && sudo systemctl restart data-platform`.

The local Terraform state contains generated passwords because it creates the
Secrets Manager value. Treat state as sensitive. Before team or production
use, configure the encrypted remote backend shown in `backend.tf.example`.

## Connect

No inbound ports are open. Start a shell:

```bash
$(terraform output -raw start_session_command)
```

Forward Dagster to local port 3000:

```bash
$(terraform output -raw dagster_port_forward_command)
```

Then open <http://localhost:3000>. ClickHouse can be forwarded similarly by
changing the SSM document parameters to remote/local port `8123`.

When `enable_metabase = true`, forward Metabase to local port 3001:

```bash
$(terraform output -raw metabase_port_forward_command)
```

Then open <http://localhost:3001>. The security group still has no inbound
rules; the connection is carried by Systems Manager.

First boot builds Python dependencies and may take several minutes. Diagnose
it from a Session Manager shell:

```bash
sudo tail -n 200 /var/log/data-platform-bootstrap.log
sudo systemctl status data-platform
cd /opt/data-platform
sudo docker compose --env-file .env ps
sudo docker compose --env-file .env logs --tail=200
```

## Load S3 data

Terraform outputs the data-lake bucket:

```bash
aws s3 cp example.parquet \
  "s3://$(terraform output -raw data_lake_bucket)/landing/orders/example.parquet"
```

Enable `aws_s3_landing` in `config/sources.aws.yml`, run `terraform apply` to
upload the changed bundle, and follow the update procedure below. The instance
role already has scoped read/write access to `landing/`, `staging/`, and
`exports/`.

## Update application code

`terraform apply` uploads the current repository bundle to the versioned S3
artifact key. Existing EC2 instances do not rerun cloud-init automatically.
After apply, use a Session Manager shell:

```bash
sudo -i
cd /opt/data-platform
aws s3 cp "s3://$(awk -F= '/^DATA_LAKE_BUCKET=/{print $2}' .env)/artifacts/platform-bundle.zip" /tmp/platform-bundle.zip
unzip -oq /tmp/platform-bundle.zip -d /opt/data-platform
systemctl restart data-platform
```

The systemd unit preserves the configured Compose profiles and Docker volumes,
so ClickHouse, Dagster, and Metabase data remain in place. Test updates in a
non-production environment first.

## Configure external database/API secrets

Terraform creates placeholders in one JSON Secrets Manager secret. Updating
that secret does not automatically rewrite the instance `.env`; this is
intentional to avoid surprise restarts. Fetch the new secret in an SSM session,
update `/opt/data-platform/.env` with mode `0600`, enable the connector YAML,
and rebuild/restart the stack.

For a larger deployment, manage each source credential as its own secret and
add only its ARN to the instance role.

## Sizing and persistence

The default `t4g.medium` is a minimum practical starting point for a core demo
or light workload. Enable Metabase on an instance with at least 8 GiB of
memory, such as `t4g.large`; the example reserves a 1 GiB Java heap while
leaving memory for ClickHouse, PostgreSQL, Dagster, and the operating system.
Move to a fixed-performance M or memory-optimized R instance when ClickHouse
has sustained CPU or memory demand. Set `cpu_credits = null` for non-T families
and keep `architecture` aligned with the instance type.

ClickHouse, Dagster, and Metabase PostgreSQL volumes live on the encrypted root
EBS volume. They survive reboots and stop/start, but not instance replacement
or Terraform destroy. Establish snapshots, database backups, and restore tests
before placing important data on this deployment. Protect the Metabase
encryption key alongside its database backup.

The S3 bucket is encrypted, versioned, non-public, and protected from accidental
Terraform deletion by `bucket_force_destroy = false`.

## Destroy

The bucket normally contains the deployment artifact, so a safe destroy will
stop rather than delete it. Empty/version-delete the bucket deliberately, or
set `bucket_force_destroy = true` only when permanent removal is intended:

```bash
terraform destroy
```

Secrets Manager uses a seven-day recovery window.
