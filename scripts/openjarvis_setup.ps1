$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$oj = Join-Path $root "external\OpenJarvis"
if (!(Test-Path $oj)) { throw "OpenJarvis submodule not found at $oj. Run: git submodule update --init --recursive" }
Set-Location $oj
if (!(Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv is required. Install from https://docs.astral.sh/uv/" }
uv sync --extra dev
Write-Host "OpenJarvis dependencies installed in $oj" -ForegroundColor Green
Write-Host "Try: cd external\OpenJarvis; uv run jarvis doctor"
