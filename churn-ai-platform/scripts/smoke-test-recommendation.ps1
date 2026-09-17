param(
  [int]$UserId = 1001,
  [int]$TopN = 3
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$BackendBase = "http://localhost:5055"
$MlBase = "http://localhost:8000"

function Get-Json {
  param([string]$Url, [string]$Method = "GET", [string]$Body = $null)
  if ($Body) {
    return Invoke-RestMethod -Uri $Url -Method $Method -ContentType "application/json" -Body $Body
  }
  return Invoke-RestMethod -Uri $Url -Method $Method
}

Write-Host "Checking ML health..."
$mlHealth = Get-Json -Url "$MlBase/health"
$mlHealth | ConvertTo-Json -Depth 8

Write-Host "Checking backend health..."
$backendHealth = Get-Json -Url "$BackendBase/health"
$backendHealth | ConvertTo-Json -Depth 8

Write-Host "Calling recommendation endpoint..."
$recommendation = Get-Json -Url "$BackendBase/recommend/$UserId" -Method "POST"
$recommendation | ConvertTo-Json -Depth 10

Write-Host "Verifying stored recommendations..."
$mysqlQuery = "SELECT user_id,item_id,score,rank_position,source,generated_at FROM recommendations WHERE user_id=$UserId ORDER BY generated_at DESC, rank_position ASC LIMIT $TopN;"
$mysqlResult = & mysql -u churn_user -pchurn_password -D churn_platform -e $mysqlQuery
Write-Host $mysqlResult
