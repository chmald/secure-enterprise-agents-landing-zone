param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
$source = Join-Path $Root "config\profiles"
if (-not (Test-Path $source)) {
    throw "Profile source folder not found: $source"
}

foreach ($image in @("src\agents\maf", "src\agents\langgraph", "src\catalog-mcp", "src\records-api")) {
    $destination = Join-Path $Root "$image\profiles"
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -Path (Join-Path $source "*.json") -Destination $destination -Force
}

Write-Host "Synced config\profiles into both hosted-agent and both tool image contexts."
