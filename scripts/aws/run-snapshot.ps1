param(
    [string]$TerraformPath = "infra/aws/terraform",

    [switch]$AssignPublicIp
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$terraformFullPath = Join-Path $repoRoot $TerraformPath

$clusterName = terraform -chdir="$terraformFullPath" output -raw ecs_cluster_name
$taskDefinitionArn = terraform -chdir="$terraformFullPath" output -raw ecs_task_definition_arn
$subnetIds = terraform -chdir="$terraformFullPath" output -json runtime_subnet_ids | ConvertFrom-Json
$securityGroupIds = terraform -chdir="$terraformFullPath" output -json ecs_security_group_ids | ConvertFrom-Json

if (-not $clusterName -or -not $taskDefinitionArn) {
    throw "Missing ECS outputs from Terraform state. Apply Terraform first."
}

if (-not $subnetIds -or $subnetIds.Count -eq 0) {
    throw "No subnet IDs found in Terraform outputs."
}

if (-not $securityGroupIds -or $securityGroupIds.Count -eq 0) {
    throw "No security group IDs found in Terraform outputs."
}

$assignPublicIpValue = if ($AssignPublicIp) { "ENABLED" } else { "DISABLED" }
$subnetsValue = ($subnetIds -join ",")
$securityGroupsValue = ($securityGroupIds -join ",")
$networkConfiguration = "awsvpcConfiguration={subnets=[$subnetsValue],securityGroups=[$securityGroupsValue],assignPublicIp=$assignPublicIpValue}"

aws ecs run-task `
    --cluster $clusterName `
    --launch-type FARGATE `
    --task-definition $taskDefinitionArn `
    --network-configuration $networkConfiguration