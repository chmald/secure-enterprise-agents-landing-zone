. "$PSScriptRoot\common.ps1"
. "$PSScriptRoot\console-auth.ps1"

$envName = Get-EnvValue -Name "AZURE_ENV_NAME"
$location = Get-EnvValue -Name "AZURE_LOCATION" -Default "eastus2"
$tenantId = Get-EnvValue -Name "AZURE_TENANT_ID"
$subscriptionId = Get-EnvValue -Name "AZURE_SUBSCRIPTION_ID"
$mode = Get-EnvValue -Name "AI_GATEWAY_MODE" -Default "apimv2"
$aiGatewayTierLocation = Get-EnvValue -Name "AI_GATEWAY_TIER_LOCATION" -Default "eastus2"
$sku = Get-EnvValue -Name "APIM_SKU" -Default "StandardV2"
$network = Get-EnvValue -Name "NETWORK_ISOLATION" -Default "false"

Assert-EnvName -EnvironmentName $envName
Assert-AzContextMatches -TenantId $tenantId -SubscriptionId $subscriptionId
Assert-AllowedValue -Name "AI_GATEWAY_MODE" -Value $mode -Allowed @("apimv2", "aigateway", "both")
if (Test-AiGatewayTierEnabled -Mode $mode) {
    Assert-AiGatewayTierLocation -Location $aiGatewayTierLocation
}
Assert-AllowedValue -Name "APIM_SKU" -Value $sku -Allowed @("StandardV2", "PremiumV2")
Assert-AllowedValue -Name "NETWORK_ISOLATION" -Value $network -Allowed @("true", "false")
$keyDelivery = Get-AiGatewayKeyDelivery
if ([string]::IsNullOrWhiteSpace((Get-EnvValue -Name "AIGW_KEY_DELIVERY"))) {
    Set-AzdEnvironmentValue -Name "AIGW_KEY_DELIVERY" -Value $keyDelivery
}
if ($keyDelivery -eq "env") {
    Write-Host "AIGW_KEY_DELIVERY=env: the AI Gateway runtime key will be passed to hosted agents as a plaintext env var (AIGW_RUNTIME_KEY). Demo-only compromise for subscriptions where policy keeps Key Vault unreachable from the agent runtime; prefer 'keyvault' (default) and NETWORK_ISOLATION=true." -ForegroundColor Yellow
}
if ($network -eq "true") {
    Write-Host "NETWORK_ISOLATION=true: private endpoints + private DNS are created and public access is disabled on Foundry/Key Vault/ACR/Cosmos/Storage/Search." -ForegroundColor Cyan
    Write-Host "  Run 'azd deploy' / data-plane steps from inside the VNet (runner, jump box, VPN). ACR switches to Premium (cost)." -ForegroundColor Cyan
    if ((Test-AiGatewayTierEnabled -Mode $mode) -and $aiGatewayTierLocation -ne $location) {
        Write-Host "WARNING: AI Gateway tier region '$aiGatewayTierLocation' differs from AZURE_LOCATION '$location'; outbound VNet integration is skipped, so the tier cannot reach the private Foundry account. Use the same region (eastus2 or swedencentral)." -ForegroundColor Yellow
    }
}

$gatewayClientId = Ensure-GatewayAppRegistration -EnvironmentName $envName
Write-Host "Gateway application client id: $gatewayClientId"
Initialize-DemoConsoleAuth -EnvironmentName $envName
Initialize-DemoOboAuth -EnvironmentName $envName

Invoke-SoftDeletePrompts -EnvironmentName $envName -Location $location

Write-Host "Preprovision checks passed for '$envName'."
