param(
    [switch]$Lan,
    [switch]$NoOllama,
    [switch]$SkipPull
)

# Pull the latest code, rebuild the dashboard and restart JARVIS.
# Use after pushing changes from another machine or editing on GitHub.
$ErrorActionPreference = "Stop"
$Root = "C:\JARVIS"

if (-not $SkipPull) {
    Write-Host "Pulling latest code..."
    git -C $Root pull --ff-only
    if ($LASTEXITCODE -ne 0) {
        Write-Host "git pull failed. Commit/stash local changes, then run again."
        exit 1
    }
}

Write-Host "Building the dashboard..."
Push-Location "$Root\frontend"
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
} finally {
    Pop-Location
}

Write-Host "Restarting JARVIS..."
& "$Root\scripts\stop_prod.ps1" | Out-Null
Start-Sleep -Seconds 2

if ($Lan -and $NoOllama) {
    & "$Root\scripts\start_prod.ps1" -Lan -NoOllama
} elseif ($Lan) {
    & "$Root\scripts\start_prod.ps1" -Lan
} elseif ($NoOllama) {
    & "$Root\scripts\start_prod.ps1" -NoOllama
} else {
    & "$Root\scripts\start_prod.ps1"
}
