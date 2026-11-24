function Get-ProjectRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-ProjectPython([string] $ProjectRoot) {
    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "Project environment not found. Create it with: python -m venv .venv; then install requirements.txt."
    }
    return $python
}

function Test-ListeningPort([int] $Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Get-BackendEnvironment([string] $ProjectRoot, [string] $Name) {
    $envFile = Join-Path $ProjectRoot "backend\.env"
    if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
        return $null
    }
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.*?)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Write-ProviderConfigurationStatus([string] $ProjectRoot) {
    $provider = Get-BackendEnvironment $ProjectRoot "LLM_PROVIDER"
    if (-not $provider) { $provider = "google" }
    if ($provider -eq "openai_compatible") {
        $configured = (Get-BackendEnvironment $ProjectRoot "OPENAI_API_KEY") -and (Get-BackendEnvironment $ProjectRoot "OPENAI_BASE_URL")
    }
    else {
        $configured = Get-BackendEnvironment $ProjectRoot "GOOGLE_API_KEY"
    }
    if ($configured) {
        Write-Host "Provider settings are present in backend/.env. Reachability will be checked when you make a request."
    }
    else {
        Write-Warning "Provider credentials are not configured. Backend and UI can start, but model-backed chat requires a key in backend/.env."
    }
}
