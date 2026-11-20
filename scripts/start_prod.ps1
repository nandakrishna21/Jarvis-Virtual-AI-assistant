param(
    [int]$Port = 8000,
    [switch]$NoOllama,
    [switch]$Lan
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

function Get-LanAddress {
    try {
        $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254*" -and $_.PrefixOrigin -ne "WellKnown" } |
            Sort-Object InterfaceMetric |
            Select-Object -First 1 -ExpandProperty IPAddress
        return $ip
    } catch {
        return $null
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

$HostAddress = "127.0.0.1"
if ($Lan) {
    $HostAddress = "0.0.0.0"
    $lanIp = Get-LanAddress
    Write-Host "LAN mode: the server will listen on every network interface."
    if ($lanIp) {
        Write-Host "Open JARVIS on your phone at: http://${lanIp}:$Port"
    } else {
        Write-Host "Could not detect a LAN address. Check your Wi-Fi connection."
    }
    Write-Host "LAN mode requires JARVIS_API_KEY in backend\.env (every API call asks for it)."
    $env:JARVIS_LAN_MODE = "true"
}

Write-Host "Starting JARVIS backend on http://${HostAddress}:$Port (API + dashboard)"
Start-Process -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "$HostAddress", "--port", "$Port", "--workers", "1" `
    -WorkingDirectory "$Root\backend" -WindowStyle Hidden `
    -RedirectStandardOutput "$Logs\backend.log" -RedirectStandardError "$Logs\backend.err.log"

$ok = $false
for ($i = 0; $i - 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { }
}

if ($ok) {
    Write-Host "JARVIS is up: http://127.0.0.1:$Port"
    if ($Lan) {
        $lanIp = Get-LanAddress
        if ($lanIp) {
            Write-Host "Phone / tablet URL: http://${lanIp}:$Port"
            Write-Host "On the phone: open that URL, then use the browser menu - Install app / Add to Home Screen."
            Write-Host "Note: installing as an app with offline support needs HTTPS. Without it, add it as a home-screen shortcut - the app still works on Wi-Fi."
        }
    }
} else {
    Write-Host "Backend did not become healthy. Check $Logs\backend.err.log"
    exit 1
}
