param(
    [switch]$SkipInstall,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ReviewAssist = Join-Path $RepoRoot ".venv\Scripts\review-assist.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating local virtual environment..."
    python -m venv .venv
}

if (-not $SkipInstall) {
    Write-Host "Installing package and development dependencies..."
    & $Python -m pip install -e ".[dev]"
}

Write-Host "Running pytest..."
& $Python -m pytest

if (-not $SkipSmoke) {
    Write-Host "Running CLI smoke checks..."
    & $ReviewAssist inspect-project projects/trails
    & $ReviewAssist inspect-project projects/conexon_projects
    & $ReviewAssist build-project-geometry projects/trails
    & $ReviewAssist build-project-geometry projects/conexon_projects
    & $ReviewAssist list-sources projects/trails
    & $ReviewAssist resolve-source-gaps projects/trails
    & $ReviewAssist analyze-constraints projects/trails
    & $ReviewAssist analyze-constraints projects/conexon_projects
    & $ReviewAssist populate-for-review projects/trails
    & $ReviewAssist populate-for-review projects/conexon_projects
    & $ReviewAssist list-review-queue projects/trails
    & $ReviewAssist list-review-queue projects/conexon_projects
}

Write-Host "Verification complete."
