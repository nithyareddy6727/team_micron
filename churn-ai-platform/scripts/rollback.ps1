param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('staging', 'production')]
    [string]$Environment,

    [string]$Namespace = ""
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "config/environments/$Environment.env.example"

if (-not $Namespace) {
    if (-not (Test-Path $configPath)) {
        throw "Config template not found: $configPath"
    }

    Get-Content $configPath | ForEach-Object {
        $line = $_.Trim()
        if ($line.StartsWith('K8S_NAMESPACE=')) {
            $Namespace = $line.Split('=', 2)[1]
        }
    }
}

if (-not $Namespace) {
    throw "K8S_NAMESPACE could not be resolved"
}

kubectl -n $Namespace rollout undo deployment/backend
kubectl -n $Namespace rollout undo deployment/ml-service
kubectl -n $Namespace rollout undo deployment/worker

kubectl -n $Namespace rollout status deployment/backend --timeout=300s
kubectl -n $Namespace rollout status deployment/ml-service --timeout=300s
kubectl -n $Namespace rollout status deployment/worker --timeout=300s

Write-Host "Rollback completed in namespace $Namespace"
