param(
    [string]$TerraformPath = "infra/aws/terraform",

    [string]$VarFile = "terraform.tfvars"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$terraformFullPath = Join-Path $repoRoot $TerraformPath

if (-not (Test-Path (Join-Path $terraformFullPath $VarFile))) {
    throw "Missing var file: $(Join-Path $terraformFullPath $VarFile)"
}

terraform -chdir=$terraformFullPath init
terraform -chdir=$terraformFullPath apply -var-file=$VarFile