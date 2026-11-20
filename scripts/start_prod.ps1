param(
    [int]$Port = 8000,
    [switch]$NoOllama
)

$ErrorActionPreference = "Continue"
$Root = "C:\JARVIS"
$Python = "$Root\backend\.venv\Scripts\python.exe"
$Logs = "$Root\logs"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "Virtualenv python not found: $Python"
    exit 1
}
if (-not (Test-Path -LiteralPath $Logs)) {
    New-Item -ItemType Directory -Path $Logs | Out-Null
}

function Test-Port([int]$PortNumber) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("127.0.0.1", $PortNumber)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

if (-not $NoOllama) {
    if (-not (Test-Port 11434)) {
        $ollama = Get-Command ollama -ErrorAction SilentlyContinue
        if ($ollama) {
            Write-Host "Starting Ollama..."
            Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden `
                -RedirectStandardOutput "$Logs\ollama.log" -RedirectStandardError "$Logs\ollama.err.log"
            Start-Sleep -Seconds 5
        } else {
            Write-Host "Ollama not on PATH - skipping local model server."
        }
    } else {
        Write-Host "Ollama already running."
    }
}

if (Test-Port $Port) {
    Write-Host "Backend already listening on $Port - nothing to start."
    exit 0
}

Write-Host "Starting JARVIS backend on http://127.0.0.1:$Port (API + dashboard)"
Start-Process -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port", "--workers", "1" `
    -WorkingDirectory "$Root\backend" -WindowStyle Hidden `
    -RedirectStandardOutput "$Logs\backend.log" -RedirectStandardError "$Logs\backend.err.log"

$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { }
}

if ($ok) {
    Write-Host "JARVIS is up: http://127.0.0.1:$Port"
} else {
    Write-Host "Backend did not become healthy. Check $Logs\backend.err.log"
    exit 1
}
