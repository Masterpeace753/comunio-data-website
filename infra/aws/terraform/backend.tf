# AP-10a: remote Terraform state backend (S3 with native lockfile).
#
# This block is enabled after bootstrap resources (state_backend.tf) have been
# applied, enabling state locking and versioning. The backend uses Terraform's
# native S3 lockfile; the existing DynamoDB table is retained as a legacy
# managed resource and is not referenced by the active backend.

terraform {
  backend "s3" {
    bucket       = "comunio-prod-tfstate"
    key          = "comunio-prod/terraform.tfstate"
    region       = "eu-central-1"
    use_lockfile = true
    encrypt      = true
  }
}
