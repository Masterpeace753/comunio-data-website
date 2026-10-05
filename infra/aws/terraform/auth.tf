variable "auth_secret_arn" {
  description = "Secrets Manager ARN containing API authentication credentials; read by the API application at runtime"
  type        = string
  default     = null

  validation {
    condition     = var.auth_secret_arn == null || can(regex("^arn:[^:]+:secretsmanager:[^:]+:[0-9]{12}:secret:.+$", var.auth_secret_arn))
    error_message = "auth_secret_arn must be a Secrets Manager secret ARN."
  }
}

data "aws_iam_policy_document" "api_auth_secret" {
  count = var.api_enabled && var.auth_secret_arn != null ? 1 : 0

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.auth_secret_arn]
  }
}

resource "aws_iam_role_policy" "api_auth_secret" {
  count = var.api_enabled && var.auth_secret_arn != null ? 1 : 0

  name   = "${local.name_prefix}-api-auth-secret"
  role   = aws_iam_role.api_task[0].id
  policy = data.aws_iam_policy_document.api_auth_secret[0].json
}
