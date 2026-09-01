# AP-10a: remote Terraform state backend (S3 + DynamoDB lock table).
#
# This block is enabled after bootstrap resources (state_backend.tf) have been
# applied, enabling state locking and versioning. Activation via terraform init
# -migrate-state moves the local state to S3 (one-time migration).

terraform {
  backend "s3" {
    bucket         = "comunio-prod-tfstate"
    key            = "comunio-prod/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "comunio-prod-tfstate-lock"
    encrypt        = true
  }
}
