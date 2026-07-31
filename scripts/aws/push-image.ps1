param(
    [Parameter(Mandatory = $true)]
    [string]$Region,

    [string]$RepositoryName = "comunio-backend-ingest",

    [string]$ImageTag = "latest",

    [string]$BackendPath = "backend"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$backendFullPath = Join-Path $repoRoot $BackendPath

$accountId = aws sts get-caller-identity --query Account --output text
if (-not $accountId) {
    throw "Could not resolve AWS account ID. Check your AWS CLI authentication."
}

$repositoryUri = "${accountId}.dkr.ecr.${Region}.amazonaws.com/${RepositoryName}"

Set-Location $backendFullPath

docker build -t "${RepositoryName}:${ImageTag}" .
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "${accountId}.dkr.ecr.${Region}.amazonaws.com"
docker tag "${RepositoryName}:${ImageTag}" "${repositoryUri}:${ImageTag}"
docker push "${repositoryUri}:${ImageTag}"

Write-Output "Pushed image: ${repositoryUri}:${ImageTag}"