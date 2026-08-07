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
docker compose --env-file .env up -d --build
```

The command keeps Docker volumes and therefore ClickHouse/Dagster data in
place. Test updates in a non-production environment first.

## Configure external database/API secrets

Terraform creates placeholders in one JSON Secrets Manager secret. Updating
that secret does not automatically rewrite the instance `.env`; this is
intentional to avoid surprise restarts. Fetch the new secret in an SSM session,
update `/opt/data-platform/.env` with mode `0600`, enable the connector YAML,
and rebuild/restart the stack.

For a larger deployment, manage each source credential as its own secret and
add only its ARN to the instance role.

## Sizing and persistence

The default `t4g.medium` is a minimum practical starting point for a demo or
light workload. It uses Arm64 images and standard T-instance CPU credits. Move
to a fixed-performance M or memory-optimized R instance when ClickHouse has
sustained CPU or memory demand; set `cpu_credits = null` for non-T families and
keep `architecture` aligned with the instance type.

ClickHouse and Dagster volumes live on the encrypted root EBS volume. They
survive reboots and stop/start, but not instance replacement or Terraform
destroy. Establish snapshots/ClickHouse backups and restore tests before
placing important data on this deployment.

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
