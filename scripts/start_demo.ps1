$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$projectRoot = Get-ProjectRoot
$python = Get-ProjectPython $projectRoot
Write-ProviderConfigurationStatus $projectRoot
foreach ($port in @(8000, 8501)) {
    if (Test-ListeningPort $port) {
        throw "Port $port is already in use. Stop the existing service before starting the demo."
    }
}

$runtimeDir = Join-Path $projectRoot ".runtime"
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$backendOut = Join-Path $runtimeDir "backend.stdout.log"
$backendErr = Join-Path $runtimeDir "backend.stderr.log"
$frontendOut = Join-Path $runtimeDir "frontend.stdout.log"
$frontendErr = Join-Path $runtimeDir "frontend.stderr.log"

$backend = Start-Process -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr

$healthy = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 | Out-Null
        $healthy = $true
        break
    }
    catch {
        if ($backend.HasExited) { break }
    }
}
if (-not $healthy) {
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue }
    throw "Backend did not become healthy. Read $backendErr for details."
}

$env:BACKEND_URL = "http://127.0.0.1:8000"
$frontend = Start-Process -FilePath $python `
    -ArgumentList @("-m", "streamlit", "run", "frontend/app.py", "--server.port", "8501") `
    -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr

Start-Sleep -Seconds 3
if ($frontend.HasExited) {
    throw "Streamlit did not stay running. Read $frontendErr for details."
}
Write-Host "DocuLens is starting at http://localhost:8501"
Write-Host "Backend PID: $($backend.Id); frontend PID: $($frontend.Id)"
Write-Host "Logs: $runtimeDir"
