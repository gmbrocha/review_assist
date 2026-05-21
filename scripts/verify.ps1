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

Write-Host "Checking source-data guardrails..."
$TrackedSources = & git ls-files sources
$AllowedSourceManifestPattern = '^sources/(source_warehouse_manifest\.json|.*/source_manifest\.json)$'
$BlockedTrackedSources = @(
    $TrackedSources | Where-Object { $_ -notmatch $AllowedSourceManifestPattern }
)
if ($BlockedTrackedSources.Count -gt 0) {
    throw "Root sources/ bulk files are tracked by Git. Move them out of the index before verification: $($BlockedTrackedSources -join ', ')"
}
$StagedFiles = & git diff --cached --name-only
$BlockedStagedFiles = @(
    $StagedFiles | Where-Object {
        ($_ -match '^(sources/|projects/[^/]+/layers/)' -and $_ -notmatch $AllowedSourceManifestPattern) -or
        $_ -match '\.(shp|shx|dbf|prj|cpg|qix|sbn|sbx|gdb|tif|tiff|zip)$'
    }
)
if ($BlockedStagedFiles.Count -gt 0) {
    throw "Bulk source files are staged and must not be committed: $($BlockedStagedFiles -join ', ')"
}

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
    & $ReviewAssist build-evidence-package projects/trails
    & $ReviewAssist populate-for-review projects/trails --no-gpt-drafting
    & $ReviewAssist populate-for-review projects/conexon_projects --no-gpt-drafting
    & $ReviewAssist export-report projects/trails --include-draft --format both
    & $ReviewAssist build-demo-deliverable projects/trails --format both --no-gpt-drafting
    & $ReviewAssist list-review-queue projects/trails
    & $ReviewAssist list-review-queue projects/conexon_projects
}

Write-Host "Verification complete."
