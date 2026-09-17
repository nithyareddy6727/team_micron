param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('local', 'staging', 'production')]
    [string]$Environment,

    [string]$Version = ""
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "config/environments/$Environment.env.example"

if (-not (Test-Path $configPath)) {
    throw "Config template not found: $configPath"
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $versionPath = Join-Path $repoRoot 'VERSION'
    $Version = (Get-Content $versionPath -Raw).Trim()
}

function Import-EnvFile {
    param([string]$Path)

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }
        $parts = $line.Split('=', 2)
        if ($parts.Count -eq 2) {
            Set-Item -Path "Env:$($parts[0])" -Value $parts[1]
        }
    }
}

Import-EnvFile -Path $configPath

if ($Environment -eq 'local') {
    Write-Host "Local releases are run through Docker Compose and the local app runner."
    Write-Host "Version: $Version"
    exit 0
}

if ([string]::IsNullOrWhiteSpace($env:K8S_NAMESPACE)) {
    throw "K8S_NAMESPACE must be set in $configPath"
}

$imageRepo = if ($env:GITHUB_REPOSITORY_OWNER) { $env:GITHUB_REPOSITORY_OWNER } else { 'your-org' }
$backendImage = "ghcr.io/$imageRepo/churn-backend:$Version"
$mlImage = "ghcr.io/$imageRepo/churn-ml-service:$Version"
$workerImage = "ghcr.io/$imageRepo/churn-worker:$Version"

kubectl -n $env:K8S_NAMESPACE set image deployment/backend backend=$backendImage
kubectl -n $env:K8S_NAMESPACE set image deployment/ml-service ml-service=$mlImage
kubectl -n $env:K8S_NAMESPACE set image deployment/worker worker=$workerImage

kubectl -n $env:K8S_NAMESPACE rollout status deployment/backend --timeout=300s
kubectl -n $env:K8S_NAMESPACE rollout status deployment/ml-service --timeout=300s
kubectl -n $env:K8S_NAMESPACE rollout status deployment/worker --timeout=300s

Write-Host "Release $Version deployed to $Environment"
