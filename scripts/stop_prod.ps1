param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"
$Root = "C:\JARVIS"

Write-Host "Stopping JARVIS processes..."

$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $connections) {
    $pidValue = $conn.OwningProcess
    if ($pidValue) {
        try {
            Stop-Process -Id $pidValue -Force -ErrorAction Stop
            Write-Host "Stopped process $pidValue on port $Port"
        } catch {
            Write-Host "Could not stop process $pidValue"
        }
    }
}

$ollamaConn = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $ollamaConn) {
    $pidValue = $conn.OwningProcess
    if ($pidValue) {
        try {
            Stop-Process -Id $pidValue -Force -ErrorAction Stop
            Write-Host "Stopped Ollama process $pidValue"
        } catch { }
    }
}

Write-Host "JARVIS stopped."
