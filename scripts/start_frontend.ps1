$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$projectRoot = Get-ProjectRoot
$python = Get-ProjectPython $projectRoot
if (Test-ListeningPort 8501) {
    throw "Port 8501 is already in use. Stop the existing Streamlit process before continuing."
}
$env:BACKEND_URL = if ($env:BACKEND_URL) { $env:BACKEND_URL } else { "http://127.0.0.1:8000" }
try {
    Invoke-RestMethod -Uri "$($env:BACKEND_URL.TrimEnd('/'))/health" -TimeoutSec 3 | Out-Null
}
catch {
    throw "Backend health check failed at $($env:BACKEND_URL). Start it with .\scripts\start_backend.ps1 first."
}
Push-Location $projectRoot
try {
    Write-Host "Starting DocuLens at http://localhost:8501"
    & $python -m streamlit run frontend/app.py --server.port 8501
    if ($LASTEXITCODE -ne 0) {
        throw "Streamlit exited with code $LASTEXITCODE. Check installed dependencies and the frontend log."
    }
}
finally {
    Pop-Location
}
