<#
.SYNOPSIS
  Start the TAP local development stack (Postgres, Redis, NATS, Qdrant,
  Temporal, OPA), wait for health, apply the DB schema, and seed a demo tenant.

.EXAMPLE
  ./scripts/dev-up.ps1
  ./scripts/dev-up.ps1 -NoSeed
#>
[CmdletBinding()]
param(
    [switch]$NoSeed,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepoRoot "platform/docker-compose.dev.yaml"
$SchemaFile = Join-Path $RepoRoot "platform/db/schema.sql"
$Project = "tap-dev"

function Write-Log([string]$Message) { Write-Host "[dev-up] $Message" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "[dev-up] $Message" -ForegroundColor Red; exit 1 }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "docker is required" }
docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "docker compose v2 is required" }
if (-not (Test-Path $ComposeFile)) { Fail "compose file not found: $ComposeFile" }

Write-Log "Starting compose stack ($ComposeFile)"
docker compose -f $ComposeFile -p $Project up -d --remove-orphans
if ($LASTEXITCODE -ne 0) { Fail "docker compose up failed" }

Write-Log "Waiting for services to report healthy (timeout ${TimeoutSeconds}s)"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ($true) {
    $unhealthy = @()
    $ids = docker compose -f $ComposeFile -p $Project ps -q
    foreach ($cid in $ids) {
        if ([string]::IsNullOrWhiteSpace($cid)) { continue }
        $line = docker inspect -f '{{.Name}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $cid
        $parts = $line.Split('|')
        $name = $parts[0]; $state = $parts[1]; $health = $parts[2]
        if ($state -ne "running" -or ($health -ne "none" -and $health -ne "healthy")) {
            $unhealthy += "${name}: $state/$health"
        }
    }
    if ($unhealthy.Count -eq 0) { Write-Log "All services healthy"; break }
    if ((Get-Date) -gt $deadline) {
        $unhealthy | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
        Fail "services not healthy after ${TimeoutSeconds}s"
    }
    Start-Sleep -Seconds 3
}

if (Test-Path $SchemaFile) {
    Write-Log "Applying database schema"
    $dbUser = if ($env:TAP_DB_USER) { $env:TAP_DB_USER } else { "tap" }
    $dbName = if ($env:TAP_DB_NAME) { $env:TAP_DB_NAME } else { "tap" }
    Get-Content $SchemaFile -Raw |
        docker compose -f $ComposeFile -p $Project exec -T postgres `
            psql -v ON_ERROR_STOP=1 -U $dbUser -d $dbName
    if ($LASTEXITCODE -ne 0) { Fail "schema apply failed" }
} else {
    Write-Log "No schema file at platform/db/schema.sql - skipping"
}

if (-not $NoSeed) {
    Write-Log "Seeding demo tenant"
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        python (Join-Path $RepoRoot "scripts/seed-demo.py")
        if ($LASTEXITCODE -ne 0) {
            Write-Log "seed failed (is tap-server running?); rerun: python scripts/seed-demo.py"
        }
    } else {
        Write-Log "python not found - skipping seed"
    }
}

Write-Log "Dev stack is up:"
Write-Log "  Postgres   localhost:5432   Redis    localhost:6379"
Write-Log "  NATS       localhost:4222   Qdrant   localhost:6333"
Write-Log "  Temporal   localhost:7233 (UI :8233)   OPA   localhost:8181"
Write-Log "Next: pip install -e ./platform -e ./sdk; tap-server --config platform/config/dev.yaml"
