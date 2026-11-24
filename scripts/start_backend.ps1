$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$projectRoot = Get-ProjectRoot
$python = Get-ProjectPython $projectRoot
Write-ProviderConfigurationStatus $projectRoot
if (Test-ListeningPort 8000) {
    throw "Port 8000 is already in use. Stop the existing backend or update scripts/start_backend.ps1 before continuing."
}
Push-Location $projectRoot
try {
    Write-Host "Starting FastAPI on http://127.0.0.1:8000"
    & $python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) {
        throw "FastAPI exited with code $LASTEXITCODE. Check installed dependencies and backend configuration."
    }
}
finally {
    Pop-Location
}
