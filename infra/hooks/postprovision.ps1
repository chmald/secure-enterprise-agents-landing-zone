. "$PSScriptRoot\common.ps1"
. "$PSScriptRoot\console-auth.ps1"

Assert-AzContextMatches -TenantId (Get-EnvValue -Name "AZURE_TENANT_ID") -SubscriptionId (Get-EnvValue -Name "AZURE_SUBSCRIPTION_ID")
Set-DemoConsoleRedirectUri
Set-DemoOboRedirectUri

$root = Get-DemoRoot
$idsPath = Join-Path $root "demo-ids.local.json"
Write-DemoIdsFile -Path $idsPath
Write-Host "Wrote local deployment IDs to $idsPath"

$enableEntraDiagnostics = Get-EnvValue -Name "ENABLE_ENTRA_DIAGNOSTICS" -Default "false"
if ($enableEntraDiagnostics -eq "true") {
    $scriptPath = Join-Path $root "scripts\Enable-EntraDiagnostics.ps1"
    if (Test-Path $scriptPath) {
        $tenantId = Get-EnvValue -Name "AZURE_TENANT_ID"
        $workspaceResourceId = Get-EnvValue -Name "LOG_ANALYTICS_WORKSPACE_ID"
        & $scriptPath -TenantId $tenantId -LogAnalyticsWorkspaceResourceId $workspaceResourceId
        if ($LASTEXITCODE -ne 0) { throw "Enable-EntraDiagnostics.ps1 failed." }
    }
    else {
        Write-Host "ENABLE_ENTRA_DIAGNOSTICS=true but scripts\Enable-EntraDiagnostics.ps1 was not found; skipping tenant-level export setup." -ForegroundColor Yellow
    }
}

$mode = Get-EnvValue -Name "AI_GATEWAY_MODE" -Default "apimv2"
$networkIsolation = (Get-EnvValue -Name "NETWORK_ISOLATION" -Default "false") -eq "true"
$keyDelivery = Get-AiGatewayKeyDelivery
$runtimeKeyForEnv = ""
if (Test-AiGatewayTierEnabled -Mode $mode) {
    $aigwName = Get-EnvValue -Name "AIGW_GATEWAY_NAME"
    $resourceGroup = Get-EnvValue -Name "AZURE_RESOURCE_GROUP"
    $subscriptionId = Get-EnvValue -Name "AZURE_SUBSCRIPTION_ID"
    $keyVaultName = Get-EnvValue -Name "KEY_VAULT_NAME"
    $secretName = Get-EnvValue -Name "AIGW_RUNTIME_KEY_SECRET_NAME" -Default "aigw-runtime-key"
    if (-not [string]::IsNullOrWhiteSpace($aigwName) -and -not [string]::IsNullOrWhiteSpace($resourceGroup) -and -not [string]::IsNullOrWhiteSpace($subscriptionId) -and -not [string]::IsNullOrWhiteSpace($keyVaultName)) {
        try {
            if ($networkIsolation) {
                # Bicep already wrote the key via the ARM control plane; the Key Vault data plane is private so az keyvault would fail from here.
                Write-Host "NETWORK_ISOLATION=true: AI Gateway runtime key secret '$secretName' is written by Bicep via ARM; skipping Key Vault data-plane check from this workstation."
                $secretPresent = $true
            }
            else {
                # ARM control-plane read: works even when policy disables Key Vault public data-plane access (live-verified under an organization policy that disables it).
                $existing = & az rest --method get --url "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.KeyVault/vaults/$keyVaultName/secrets/${secretName}?api-version=2023-07-01" --query id -o tsv 2>$null
                $secretPresent = ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($existing))
                $global:LASTEXITCODE = 0
            }
            if ($secretPresent) {
                Write-Host "AI Gateway runtime key secret '$secretName' already present in Key Vault (set by Bicep); skipping."
            }
            else {
                $runtimeKey = Get-AiGatewayRuntimeKey -SubscriptionId $subscriptionId -ResourceGroup $resourceGroup -GatewayName $aigwName
                & az keyvault secret set --vault-name $keyVaultName --name $secretName --value $runtimeKey --only-show-errors | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "az keyvault secret set failed with exit code $LASTEXITCODE." }
                Write-Host "Stored AI Gateway runtime access key 'agents' in Key Vault secret '$secretName'."
            }
        }
        catch {
            Write-Host "AI Gateway runtime key could not be stored automatically: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "Portal fallback: open https://ai.gateway.azure.com, select gateway '$aigwName', copy runtime key 'agents' (apiKeys/agents/listSecrets), then store it in Key Vault '$keyVaultName' as secret '$secretName'." -ForegroundColor Yellow
        }
        if ($keyDelivery -eq "env") {
            # Opt-in, demo-only: hosted agents cannot reach a Key Vault whose public access policy forces off, so pass the key as an env var.
            try {
                $runtimeKeyForEnv = Get-AiGatewayRuntimeKey -SubscriptionId $subscriptionId -ResourceGroup $resourceGroup -GatewayName $aigwName
            }
            catch {
                Write-Host "AIGW_KEY_DELIVERY=env but the runtime key could not be read from the gateway: $($_.Exception.Message)" -ForegroundColor Red
                throw
            }
        }
    }
    else {
        Write-Host "Skipping AI Gateway runtime key capture because one or more required azd outputs are blank: AIGW_GATEWAY_NAME, AZURE_RESOURCE_GROUP, AZURE_SUBSCRIPTION_ID, KEY_VAULT_NAME." -ForegroundColor Yellow
    }
}

if ($keyDelivery -eq "env") {
    if (-not [string]::IsNullOrWhiteSpace($runtimeKeyForEnv)) {
        Set-AzdEnvironmentValue -Name "AIGW_RUNTIME_KEY" -Value $runtimeKeyForEnv
        Write-Host "AIGW_KEY_DELIVERY=env: stored the AI Gateway runtime key in the azd environment as AIGW_RUNTIME_KEY; 'azd deploy' passes it to hosted agents as a plaintext env var." -ForegroundColor Yellow
        Write-Host "  Demo-only compromise: the key is readable in the azd env file and the agent's configuration. Prefer AIGW_KEY_DELIVERY=keyvault, ideally with NETWORK_ISOLATION=true (Key Vault private endpoint + agent subnet injection)." -ForegroundColor Yellow
    }
    else {
        Write-Host "AIGW_KEY_DELIVERY=env but no AI Gateway runtime key was captured (AI_GATEWAY_MODE=$mode); AIGW_RUNTIME_KEY is left unchanged." -ForegroundColor Yellow
    }
}
elseif (-not [string]::IsNullOrWhiteSpace((Get-EnvValue -Name "AIGW_RUNTIME_KEY"))) {
    Set-AzdEnvironmentValue -Name "AIGW_RUNTIME_KEY" -Value ""
    Write-Host "AIGW_KEY_DELIVERY=keyvault: cleared AIGW_RUNTIME_KEY from the azd environment so no plaintext key is passed to hosted agents."
}

if ($mode -eq "apimv2" -or $mode -eq "both") {
    Write-Host "Register the APIM v2 gateway with the Microsoft Foundry project from the Foundry portal: Manage > AI Gateway > Register existing API Management gateway."
}
else {
    Write-Host "AI Gateway tier resources (Microsoft.ApiManagement/service, sku AIGateway) were provisioned with model provider, alias, tool servers and runtime key. To register the gateway as a Foundry connection use the Foundry portal: Manage > AI Gateway."
}

if ($networkIsolation) {
    $acrName = Get-EnvValue -Name "ACR_NAME" -Default "<acr-name>"
    $rg = Get-EnvValue -Name "AZURE_RESOURCE_GROUP" -Default "<resource-group>"
    $apimName = Get-EnvValue -Name "APIM_NAME" -Default "<apim-name>"
    Write-Host ""
    Write-Host "NETWORK_ISOLATION=true - private endpoints, private DNS zones and agent-subnet injection were provisioned." -ForegroundColor Cyan
    Write-Host "  - Foundry account, Key Vault, ACR, Cosmos, Storage, Search and the gateway have public access disabled (APIM / AI Gateway inbound stays public until you lock it down, see below)." -ForegroundColor Cyan
    Write-Host "  - Data-plane steps (azd deploy / ACR push, 'az keyvault secret ...', Foundry agent create/invoke) only work from INSIDE the VNet:" -ForegroundColor Yellow
    Write-Host "      run azd from a self-hosted runner / jump box / Bastion VM / VPN-connected machine in the peered network, or temporarily allow your IP:" -ForegroundColor Yellow
    Write-Host "      az acr update --name $acrName --public-network-enabled true   (revert afterwards with --public-network-enabled false)" -ForegroundColor Yellow
    Write-Host "  - The hosted-agent endpoint itself stays public (azd cannot make it private yet)." -ForegroundColor Yellow
    if ($mode -eq "apimv2" -or $mode -eq "both") {
        Write-Host "  - APIM v2 inbound private endpoint exists; public access can only be disabled once it exists. Lock down with:" -ForegroundColor Yellow
        Write-Host "      az rest --method patch --url https://management.azure.com/subscriptions/<sub>/resourceGroups/$rg/providers/Microsoft.ApiManagement/service/$apimName?api-version=2024-05-01 --body '{\"properties\":{\"publicNetworkAccess\":\"Disabled\"}}'" -ForegroundColor Yellow
        Write-Host "    Do this only after confirming the Foundry Agent Service path can still reach the gateway (managed inference plane)." -ForegroundColor Yellow
    }
    if (Test-AiGatewayTierEnabled -Mode $mode) {
        Write-Host "  - AI Gateway tier inbound private endpoint is a PREVIEW feature (see docs/10); verify it in the portal, then optionally disable public network access." -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host "No sample data was seeded by infra hooks. Runtime seed behavior is controlled by SEED_SAMPLE_DATA and the code scripts."
