param(
    [string]$EnvironmentName = $env:AZURE_ENV_NAME,
    [string]$AzureLocation = $(if ($env:AZURE_LOCATION) { $env:AZURE_LOCATION } else { "eastus2" }),
    [string]$AzureSubscriptionId = $env:AZURE_SUBSCRIPTION_ID,
    [string]$AzureTenantId = $env:AZURE_TENANT_ID,
    [string]$AzurePrincipalId = $env:AZURE_PRINCIPAL_ID,
    [string]$AzurePrincipalType = $(if ($env:AZURE_PRINCIPAL_TYPE) { $env:AZURE_PRINCIPAL_TYPE } else { "User" }),
    [string]$AzureResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$AiGatewayMode = $(if ($env:AI_GATEWAY_MODE) { $env:AI_GATEWAY_MODE } else { "apimv2" }),
    [string]$AiGatewayTierLocation = $(if ($env:AI_GATEWAY_TIER_LOCATION) { $env:AI_GATEWAY_TIER_LOCATION } else { "eastus2" }),
    [string]$ApimSku = $(if ($env:APIM_SKU) { $env:APIM_SKU } else { "StandardV2" }),
    [string]$ApimPublisherEmail = $(if ($env:APIM_PUBLISHER_EMAIL) { $env:APIM_PUBLISHER_EMAIL } else { "demo@example.com" }),
    [string]$ApimPublisherName = $(if ($env:APIM_PUBLISHER_NAME) { $env:APIM_PUBLISHER_NAME } else { "Demo Publisher" }),
    [string]$GatewayAppClientId = $env:GATEWAY_APP_CLIENT_ID,
    [int]$TokenLimitTpmPerAgent = $(if ($env:TOKEN_LIMIT_TPM_PER_AGENT) { [int]$env:TOKEN_LIMIT_TPM_PER_AGENT } else { 20000 }),
    [int]$AigwRequestLimitRpm = $(if ($env:AIGW_REQUEST_LIMIT_RPM) { [int]$env:AIGW_REQUEST_LIMIT_RPM } else { 120 }),
    [string]$AigwRuntimeKeySecretName = $(if ($env:AIGW_RUNTIME_KEY_SECRET_NAME) { $env:AIGW_RUNTIME_KEY_SECRET_NAME } else { "aigw-runtime-key" }),
    [bool]$EnableContentSafety = $(if ($env:ENABLE_CONTENT_SAFETY) { [bool]::Parse($env:ENABLE_CONTENT_SAFETY) } else { $true }),
    [bool]$EnableLlmMessageLogging = $(if ($env:ENABLE_LLM_MESSAGE_LOGGING) { [bool]::Parse($env:ENABLE_LLM_MESSAGE_LOGGING) } else { $true }),
    [bool]$NetworkIsolation = $(if ($env:NETWORK_ISOLATION) { [bool]::Parse($env:NETWORK_ISOLATION) } else { $false }),
    [string]$VnetAddressPrefix = $(if ($env:VNET_ADDRESS_PREFIX) { $env:VNET_ADDRESS_PREFIX } else { "10.40.0.0/16" }),
    [string]$AgentSubnetPrefix = $(if ($env:AGENT_SUBNET_PREFIX) { $env:AGENT_SUBNET_PREFIX } else { "10.40.0.0/24" }),
    [string]$AcaSubnetPrefix = $(if ($env:ACA_SUBNET_PREFIX) { $env:ACA_SUBNET_PREFIX } else { "10.40.2.0/23" }),
    [string]$ApimSubnetPrefix = $(if ($env:APIM_SUBNET_PREFIX) { $env:APIM_SUBNET_PREFIX } else { "10.40.4.0/27" }),
    [string]$PeSubnetPrefix = $(if ($env:PE_SUBNET_PREFIX) { $env:PE_SUBNET_PREFIX } else { "10.40.5.0/24" }),
    [string]$ModelName = $(if ($env:MODEL_NAME) { $env:MODEL_NAME } else { "gpt-5.5" }),
    [string]$ModelVersion = $(if ($env:MODEL_VERSION) { $env:MODEL_VERSION } else { "2026-04-24" }),
    [string]$ModelDeploymentName = $(if ($env:MODEL_DEPLOYMENT_NAME) { $env:MODEL_DEPLOYMENT_NAME } else { "chat" }),
    [string]$ModelSku = $(if ($env:MODEL_SKU) { $env:MODEL_SKU } else { "GlobalStandard" }),
    [int]$ModelCapacity = $(if ($env:MODEL_CAPACITY) { [int]$env:MODEL_CAPACITY } else { 50 }),
    [string]$DomainProfile = $(if ($env:DOMAIN_PROFILE) { $env:DOMAIN_PROFILE } else { "manufacturing-field-ops" }),
    [bool]$DeployAgentOnAca = $(if ($env:DEPLOY_AGENT_ON_ACA) { [bool]::Parse($env:DEPLOY_AGENT_ON_ACA) } else { $false }),
    [bool]$SeedSampleData = $(if ($env:SEED_SAMPLE_DATA) { [bool]::Parse($env:SEED_SAMPLE_DATA) } else { $true }),
    [int]$LogRetentionDays = $(if ($env:LOG_RETENTION_DAYS) { [int]$env:LOG_RETENTION_DAYS } else { 90 }),
    [bool]$EnableAlerts = $(if ($env:ENABLE_ALERTS) { [bool]::Parse($env:ENABLE_ALERTS) } else { $true }),
    [string]$AlertEmail = $env:ALERT_EMAIL,
    [bool]$EnableActivityLogExport = $(if ($env:ENABLE_ACTIVITY_LOG_EXPORT) { [bool]::Parse($env:ENABLE_ACTIVITY_LOG_EXPORT) } else { $false }),
    [bool]$EnableSentinel = $(if ($env:ENABLE_SENTINEL) { [bool]::Parse($env:ENABLE_SENTINEL) } else { $false }),
    [bool]$EnableEntraDiagnostics = $(if ($env:ENABLE_ENTRA_DIAGNOSTICS) { [bool]::Parse($env:ENABLE_ENTRA_DIAGNOSTICS) } else { $false })
)

. "$PSScriptRoot\hooks\common.ps1"

Assert-EnvName -EnvironmentName $EnvironmentName
Assert-AzContextMatches -TenantId $AzureTenantId -SubscriptionId $AzureSubscriptionId
Assert-AllowedValue -Name "AI_GATEWAY_MODE" -Value $AiGatewayMode -Allowed @("apimv2", "aigateway", "both")
if (Test-AiGatewayTierEnabled -Mode $AiGatewayMode) {
    Assert-AiGatewayTierLocation -Location $AiGatewayTierLocation
}

$templateFile = Join-Path $PSScriptRoot "azd.bicep"
$consoleClientId = Get-EnvValue -Name "DEMO_CONSOLE_CLIENT_ID"
$consoleOwnerId = Get-EnvValue -Name "DEMO_CONSOLE_ALLOWED_USER_ID"
$consoleSecret = Get-EnvValue -Name "DEMO_CONSOLE_CLIENT_SECRET"
if (-not $consoleClientId -or -not $consoleOwnerId -or -not $consoleSecret) {
    throw "Console authentication is required. Run azd provision (which configures deployer-only Entra access), or provide DEMO_CONSOLE_CLIENT_ID, DEMO_CONSOLE_ALLOWED_USER_ID and DEMO_CONSOLE_CLIENT_SECRET."
}
$parameters = @(
    "environmentName=$EnvironmentName",
    "location=$AzureLocation",
    "subscriptionId=$AzureSubscriptionId",
    "tenantId=$AzureTenantId",
    "principalId=$AzurePrincipalId",
    "principalType=$AzurePrincipalType",
    "resourceGroupName=$AzureResourceGroup",
    "aiGatewayMode=$AiGatewayMode",
    "aiGatewayTierLocation=$AiGatewayTierLocation",
    "apimSku=$ApimSku",
    "apimPublisherEmail=$ApimPublisherEmail",
    "apimPublisherName=$ApimPublisherName",
    "gatewayAppClientId=$GatewayAppClientId",
    "demoConsoleClientId=$consoleClientId",
    "demoConsoleAllowedUserId=$consoleOwnerId",
    "demoConsoleClientSecret=$consoleSecret",
    "agentDefaultGateway=$(Get-EnvValue -Name 'AGENT_DEFAULT_GATEWAY' -Default 'apimv2')",
    "aigwKeyDelivery=$(Get-AiGatewayKeyDelivery)",
    "tokenLimitTpmPerAgent=$TokenLimitTpmPerAgent",
    "aigwRequestLimitRpm=$AigwRequestLimitRpm",
    "aigwRuntimeKeySecretName=$AigwRuntimeKeySecretName",
    "enableContentSafety=$EnableContentSafety",
    "enableLlmMessageLogging=$EnableLlmMessageLogging",
    "networkIsolation=$NetworkIsolation",
    "vnetAddressPrefix=$VnetAddressPrefix",
    "agentSubnetPrefix=$AgentSubnetPrefix",
    "acaSubnetPrefix=$AcaSubnetPrefix",
    "apimSubnetPrefix=$ApimSubnetPrefix",
    "peSubnetPrefix=$PeSubnetPrefix",
    "modelName=$ModelName",
    "modelVersion=$ModelVersion",
    "modelDeploymentName=$ModelDeploymentName",
    "modelSku=$ModelSku",
    "modelCapacity=$ModelCapacity",
    "domainProfile=$DomainProfile",
    "deployAgentOnAca=$DeployAgentOnAca",
    "seedSampleData=$SeedSampleData",
    "logRetentionDays=$LogRetentionDays",
    "enableAlerts=$EnableAlerts",
    "alertEmail=$AlertEmail",
    "enableActivityLogExport=$EnableActivityLogExport",
    "enableSentinel=$EnableSentinel",
    "enableEntraDiagnostics=$EnableEntraDiagnostics"
)

az deployment sub create `
    --name "foundry-hosted-agents-$EnvironmentName" `
    --location $AzureLocation `
    --subscription $AzureSubscriptionId `
    --template-file $templateFile `
    --parameters $parameters

if ($LASTEXITCODE -ne 0) {
    throw "Deployment failed."
}
