resource "aws_secretsmanager_secret" "database" {
  name                    = "${local.name}/database"
  recovery_window_in_days = 7
}
resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    database_url = "postgresql+asyncpg://frontierops:${urlencode(random_password.db.result)}@${aws_db_instance.this.address}:5432/frontierops"
  })
}
resource "aws_secretsmanager_secret" "servicenow" {
  name                    = "${local.name}/servicenow"
  description             = "Populate instance_url, username, and password after provisioning"
  recovery_window_in_days = 7
}
