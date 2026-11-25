$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$oj = Join-Path $root "external\OpenJarvis"
if (!(Test-Path $oj)) { throw "OpenJarvis submodule not found at $oj" }
Set-Location $oj
if (!(Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv is required" }
uv run jarvis @args
