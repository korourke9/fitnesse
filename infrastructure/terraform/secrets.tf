# Secrets Manager Secret for Database URL
resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${var.project_name}-database-url"
  description             = "Database connection URL for Fitnesse"
  recovery_window_in_days = 7

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-database-url"
  })
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql://${var.database_username}:${var.database_password}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${var.database_name}"
}

# IAM Policy for ECS to read secrets
resource "aws_iam_role_policy" "ecs_secrets" {
  name = "${var.project_name}-ecs-secrets-policy"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.database_url.arn
      }
    ]
  })
}

