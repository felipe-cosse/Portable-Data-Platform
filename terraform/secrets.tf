resource "random_password" "clickhouse" {
  length           = 32
  special          = true
  override_special = "_%@-"
}

resource "random_password" "dagster_postgres" {
  length           = 32
  special          = true
  override_special = "_%@-"
}

resource "aws_secretsmanager_secret" "platform" {
  name_prefix             = "${var.name}/runtime-"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.name}-runtime"
  }
}

resource "aws_secretsmanager_secret_version" "platform" {
  secret_id = aws_secretsmanager_secret.platform.id
  secret_string = jsonencode({
    clickhouse_database = "analytics"
    clickhouse_user     = "platform"
    clickhouse_password = random_password.clickhouse.result
    dagster_pg_database = "dagster"
    dagster_pg_user     = "dagster"
    dagster_pg_password = random_password.dagster_postgres.result
    source_postgres_url = ""
    source_mysql_url    = ""
    example_api_token   = ""
  })
}
