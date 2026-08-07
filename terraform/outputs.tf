output "instance_id" {
  description = "EC2 instance ID used for Session Manager."
  value       = aws_instance.platform.id
}

output "data_lake_bucket" {
  description = "Versioned S3 bucket for landing, staging, exports, and deployment artifacts."
  value       = aws_s3_bucket.data_lake.id
}

output "runtime_secret_arn" {
  description = "Secret holding generated service credentials and optional source placeholders."
  value       = aws_secretsmanager_secret.platform.arn
}

output "start_session_command" {
  description = "Open a keyless shell to the platform instance."
  value       = "aws ssm start-session --region ${var.aws_region} --target ${aws_instance.platform.id}"
}

output "dagster_port_forward_command" {
  description = "Forward local port 3000 to Dagster without opening inbound network access."
  value = join(" ", [
    "aws ssm start-session",
    "--region ${var.aws_region}",
    "--target ${aws_instance.platform.id}",
    "--document-name AWS-StartPortForwardingSession",
    "--parameters 'portNumber=3000,localPortNumber=3000'",
  ])
}

output "bootstrap_log_command" {
  description = "Inspect first-boot deployment logs."
  value       = "aws ssm start-session --region ${var.aws_region} --target ${aws_instance.platform.id} --document-name AWS-StartInteractiveCommand --parameters command='sudo tail -n 200 /var/log/data-platform-bootstrap.log'"
}
