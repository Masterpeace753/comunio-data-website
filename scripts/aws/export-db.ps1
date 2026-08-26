param(
    [string]$TerraformPath = "infra/aws/terraform",
    [string]$OutputDir = "exports",
    [switch]$AssignPublicIp = $true
)

$ErrorActionPreference = "Stop"

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$terraformFullPath = Join-Path $repoRoot $TerraformPath
$outputFullPath = Join-Path $repoRoot $OutputDir

if (-not (Test-Path $outputFullPath)) {
    New-Item -ItemType Directory -Path $outputFullPath -Force | Out-Null
}

$clusterName = terraform -chdir="$terraformFullPath" output -raw ecs_cluster_name
$taskDefinitionArn = terraform -chdir="$terraformFullPath" output -raw ecs_task_definition_arn
$subnetIds = terraform -chdir="$terraformFullPath" output -json runtime_subnet_ids | ConvertFrom-Json
$securityGroupIds = terraform -chdir="$terraformFullPath" output -json ecs_security_group_ids | ConvertFrom-Json

if (-not $clusterName -or -not $taskDefinitionArn) {
    throw "Missing ECS outputs from Terraform state. Apply Terraform first."
}

$assignPublicIpValue = if ($AssignPublicIp) { "ENABLED" } else { "DISABLED" }
$subnetsValue = ($subnetIds -join ",")
$securityGroupsValue = ($securityGroupIds -join ",")
$networkConfiguration = "awsvpcConfiguration={subnets=[$subnetsValue],securityGroups=[$securityGroupsValue],assignPublicIp=$assignPublicIpValue}"

$pyCode = @'
import os, sys, io, json, psycopg2, psycopg2.extras
from datetime import datetime, date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

conn = psycopg2.connect(db_url)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;")
tables = [r['table_name'] for r in cur.fetchall()]

dump_data = {}
sql_lines = ["-- PostgreSQL Database Export", f"-- Generated: {datetime.utcnow().isoformat()} UTC\n"]

def quote_val(val):
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (datetime, date)):
        return f"'{val.isoformat()}'"
    if isinstance(val, (dict, list)):
        return f"'{json.dumps(val)}'::jsonb"
    s = str(val).replace("'", "''")
    return f"'{s}'"

for t in tables:
    cur.execute(f'SELECT * FROM "{t}" ORDER BY 1;')
    rows = cur.fetchall()
    dump_data[t] = [dict(r) for r in rows]
    if rows:
        cols = list(rows[0].keys())
        col_names = ", ".join(f'"{c}"' for c in cols)
        for r in rows:
            vals = ", ".join(quote_val(r[c]) for c in cols)
            sql_lines.append(f'INSERT INTO "{t}" ({col_names}) VALUES ({vals});')
    sql_lines.append("")

print("--- BEGIN DB DUMP SQL ---")
print("\n".join(sql_lines))
print("--- END DB DUMP SQL ---")
print("--- BEGIN DB DUMP JSON ---")
print(json.dumps(dump_data, default=lambda o: o.isoformat() if isinstance(o, (datetime, date)) else str(o), indent=2))
print("--- END DB DUMP JSON ---")
'@

$overrides = @{
    containerOverrides = @(
        @{
            name = "ingest-runner"
            command = @("python", "-c", $pyCode)
        }
    )
} | ConvertTo-Json -Depth 5 -Compress

Write-Host "Triggering ECS database export task..."
$runResultJson = aws ecs run-task `
    --cluster $clusterName `
    --launch-type FARGATE `
    --task-definition $taskDefinitionArn `
    --network-configuration $networkConfiguration `
    --overrides $overrides `
    --no-cli-pager
$runResult = $runResultJson | ConvertFrom-Json

$taskArn = $runResult.tasks[0].taskArn
$taskId = $taskArn.Split('/')[-1]
Write-Host "Task started with ID: $taskId"

Write-Host "Waiting for task $taskId to complete..."
aws ecs wait tasks-stopped --cluster $clusterName --tasks $taskArn --region eu-central-1

$taskDetailsJson = aws ecs describe-tasks --cluster $clusterName --tasks $taskArn --region eu-central-1 --no-cli-pager
$taskDetails = $taskDetailsJson | ConvertFrom-Json
$exitCode = $taskDetails.tasks[0].containers[0].exitCode

if ($exitCode -ne 0) {
    $stoppedReason = $taskDetails.tasks[0].stoppedReason
    throw "Export task failed with exit code $exitCode. Reason: $stoppedReason"
}

Write-Host "Export task completed successfully. Retrieving log output..."
$logStreamName = "ecs/ingest-runner/$taskId"

$tempDir = [System.IO.Path]::GetTempPath()
$tmpLogFile = Join-Path $tempDir "ecs_log_$taskId.json"

$allMessages = New-Object System.Collections.Generic.List[string]
$nextToken = $null

do {
    $cmdArgs = @(
        "logs", "get-log-events",
        "--log-group-name", "/ecs/comunio-prod-ingest",
        "--log-stream-name", $logStreamName,
        "--region", "eu-central-1",
        "--no-cli-pager"
    )
    if ($nextToken) {
        $cmdArgs += "--next-token"
        $cmdArgs += $nextToken
    }
    
    & aws $cmdArgs > $tmpLogFile
    $jsonContent = [System.IO.File]::ReadAllText($tmpLogFile, [System.Text.Encoding]::UTF8)
    $res = $jsonContent | ConvertFrom-Json
    Remove-Item $tmpLogFile -ErrorAction SilentlyContinue

    foreach ($evt in $res.events) {
        $allMessages.Add($evt.message)
    }
    $prevToken = $nextToken
    $nextToken = $res.nextForwardToken
    if ($res.events.Count -eq 0 -or $nextToken -eq $prevToken) {
        break
    }
} while ($nextToken)

$fullLog = $allMessages -join "`n"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$sqlPath = Join-Path $outputFullPath "db_dump_$timestamp.sql"
$jsonPath = Join-Path $outputFullPath "db_dump_$timestamp.json"

if ($fullLog -match "(?s)--- BEGIN DB DUMP SQL ---\s*(.*?)\s*--- END DB DUMP SQL ---") {
    [System.IO.File]::WriteAllText($sqlPath, $matches[1], [System.Text.Encoding]::UTF8)
    Write-Host "SQL dump saved to: $sqlPath"
} else {
    Write-Warning "Could not parse SQL dump from log output."
}

if ($fullLog -match "(?s)--- BEGIN DB DUMP JSON ---\s*(.*?)\s*--- END DB DUMP JSON ---") {
    [System.IO.File]::WriteAllText($jsonPath, $matches[1], [System.Text.Encoding]::UTF8)
    Write-Host "JSON dump saved to: $jsonPath"
} else {
    Write-Warning "Could not parse JSON dump from log output."
}
