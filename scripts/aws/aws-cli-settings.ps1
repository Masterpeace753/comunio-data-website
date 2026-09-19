$env:AWS_CLI_CONNECT_TIMEOUT = "10"
$env:AWS_CLI_READ_TIMEOUT = "30"

aws sts get-caller-identity --no-cli-pager --query Account --output text | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "AWS authentication failed or expired. Refresh the AWS CLI session before continuing."
}
