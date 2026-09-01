# AP-10a: bootstrap resources for a remote, locked Terraform state backend.
#
# Local state (terraform.tfstate) is not committed to git (see .gitignore), but it
# has no locking (risking corruption on a concurrent apply), no durability beyond a
# single disk, and no versioned recovery if deleted. These resources move state to
# S3 (versioned, encrypted, public access blocked) with DynamoDB-based locking.
#
# Bootstrap procedure (one-time, manual, run only with explicit approval):
#   1. terraform init
#   2. terraform apply -target=aws_s3_bucket.tfstate \
#        -target=aws_s3_bucket_versioning.tfstate \
#        -target=aws_s3_bucket_server_side_encryption_configuration.tfstate \
#        -target=aws_s3_bucket_public_access_block.tfstate \
#        -target=aws_s3_bucket_lifecycle_configuration.tfstate \
#        -target=aws_dynamodb_table.tfstate_lock
#   3. Uncomment the backend "s3" block in backend.tf.
#   4. terraform init -migrate-state   (confirm "yes" to copy existing local state)
#   5. terraform plan                 (verify no unexpected diff)
#
# See infra/aws/README.md for the full runbook.

resource "aws_s3_bucket" "tfstate" {
  bucket = "${local.name_prefix}-tfstate"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    id     = "expire-noncurrent-state-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_dynamodb_table" "tfstate_lock" {
  name         = "${local.name_prefix}-tfstate-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = local.common_tags
}
