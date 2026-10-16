// Main resource-group deployment for the hosted agents + gateway landing-zone demo.
targetScope = 'resourceGroup'

param environmentName string
param location string = resourceGroup().location
param subscriptionId string
param tenantId string
param principalId string = ''
@allowed([
  'User'
  'ServicePrincipal'
])
param principalType string = 'User'

@allowed([
  'apimv2'
  'aigateway'
  'both'
])
param aiGatewayMode string = 'apimv2'
@allowed([
  'eastus2'
  'swedencentral'
])
param aiGatewayTierLocation string = 'eastus2'
@allowed([
  'StandardV2'
  'PremiumV2'
])
param apimSku string = 'StandardV2'
param apimPublisherEmail string
param apimPublisherName string = 'Demo Publisher'
param gatewayAppClientId string = ''
param demoConsoleClientId string
param demoConsoleAllowedUserId string
@secure()
param demoConsoleClientSecret string
param agentDefaultGateway string = 'apimv2'
@allowed([
  'keyvault'
  'env'
])
param aigwKeyDelivery string = 'keyvault'
param tokenLimitTpmPerAgent int = 20000
param aigwRequestLimitRpm int = 120
param aigwRuntimeKeySecretName string = 'aigw-runtime-key'
param enableContentSafety bool = true
param enableLlmMessageLogging bool = true

param networkIsolation bool = false
param vnetAddressPrefix string = '10.40.0.0/16'
param agentSubnetPrefix string = '10.40.0.0/24'
param acaSubnetPrefix string = '10.40.2.0/23'
param apimSubnetPrefix string = '10.40.4.0/27'
param peSubnetPrefix string = '10.40.5.0/24'
@description('AI Gateway tier outbound VNet-integration subnet (/27 or larger, delegated Microsoft.Web/serverFarms).')
param aigwSubnetPrefix string = '10.40.6.0/27'
@description('When isolated, also create the AI Gateway tier inbound private endpoint (preview feature; set false to skip).')
param aigwInboundPrivateEndpoint bool = true

param modelName string = 'gpt-5.5'
param modelVersion string = '2026-04-24'
param modelDeploymentName string = 'chat'
param modelSku string = 'GlobalStandard'
param modelCapacity int = 50

param domainProfile string = 'manufacturing-field-ops'
param deployAgentOnAca bool = false
param seedSampleData bool = true

param logRetentionDays int = 90
param enableAlerts bool = true
param alertEmail string = ''
param enableActivityLogExport bool = false
param enableSentinel bool = false
param enableEntraDiagnostics bool = false

var normalized = toLower(environmentName)
var suffix = uniqueString(subscription().id, resourceGroup().id, normalized)
var shortSuffix = take(replace(suffix, '-', ''), 8)
var baseName = take(replace(normalized, '-', ''), 12)
var tags = {
  demo: 'foundry-hosted-agents-ai-gateway-landing-zone'
  environment: environmentName
  domainProfile: domainProfile
}
var lawName = take('law-${normalized}-${shortSuffix}', 63)
var appInsightsName = take('appi-${normalized}-${shortSuffix}', 255)
var foundryAccountName = take('fdry-${normalized}-${shortSuffix}', 64)
var foundryProjectName = take('proj-${normalized}', 64)
var acrName = take('acr${baseName}${shortSuffix}', 50)
var acaEnvName = take('cae-${normalized}-${shortSuffix}', 32)
var keyVaultName = take('kv-${normalized}-${shortSuffix}', 24)
var apimName = take('apim-${normalized}-${shortSuffix}', 50)
var aiGatewayName = take('aigw-${normalized}-${shortSuffix}', 50)
var llmApiPath = 'llm'
var deployApimV2Gateway = aiGatewayMode == 'apimv2' || aiGatewayMode == 'both'
var deployAiGatewayTier = aiGatewayMode == 'aigateway' || aiGatewayMode == 'both'
// Outbound VNet integration must be in the same region as the VNet; the AI Gateway tier is only offered in two regions.
var aigwOutboundIntegration = networkIsolation && aiGatewayTierLocation == location

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    workspaceName: lawName
    appInsightsName: appInsightsName
    retentionInDays: logRetentionDays
  }
}

module network 'modules/network.bicep' = if (networkIsolation) {
  name: 'network'
  params: {
    location: location
    tags: tags
    namePrefix: normalized
    vnetAddressPrefix: vnetAddressPrefix
    agentSubnetPrefix: agentSubnetPrefix
    acaSubnetPrefix: acaSubnetPrefix
    apimSubnetPrefix: apimSubnetPrefix
    peSubnetPrefix: peSubnetPrefix
    aigwSubnetPrefix: aigwSubnetPrefix
  }
}

module privateDns 'modules/private-dns.bicep' = if (networkIsolation) {
  name: 'private-dns'
  params: {
    tags: tags
    vnetId: network.outputs.vnetId
    namePrefix: normalized
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    tags: tags
    keyVaultName: keyVaultName
    tenantId: tenantId
    principalId: principalId
    principalType: principalType
    networkIsolation: networkIsolation
  }
}

module privateFoundryDependencies 'modules/foundry-private.bicep' = if (networkIsolation) {
  name: 'foundry-private'
  params: {
    location: location
    tags: tags
    namePrefix: normalized
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    dnsZoneIds: privateDns.outputs.zoneIds
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    location: location
    tags: tags
    aiServicesName: foundryAccountName
    aiProjectName: foundryProjectName
    modelName: modelName
    modelVersion: modelVersion
    modelDeploymentName: modelDeploymentName
    modelSku: modelSku
    modelCapacity: modelCapacity
    principalId: principalId
    principalType: principalType
    appInsightsId: monitoring.outputs.appInsightsId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    containerRegistryName: acrName
    networkIsolation: networkIsolation
    agentSubnetId: networkIsolation ? network.outputs.agentSubnetId : ''
  }
}

// Private endpoints for the control-plane-created PaaS resources (Foundry account, Key Vault, ACR).
module foundryPe 'modules/private-endpoint.bicep' = if (networkIsolation) {
  name: 'pe-foundry'
  params: {
    location: location
    tags: tags
    name: 'pe-${foundryAccountName}'
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: foundry.outputs.aiServicesId
    groupId: 'account'
    dnsZoneIds: [
      privateDns.outputs.zoneIds.cognitiveServices
      privateDns.outputs.zoneIds.openAi
      privateDns.outputs.zoneIds.servicesAi
    ]
  }
}

module keyVaultPe 'modules/private-endpoint.bicep' = if (networkIsolation) {
  name: 'pe-keyvault'
  params: {
    location: location
    tags: tags
    name: 'pe-${keyVaultName}'
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: keyvault.outputs.keyVaultId
    groupId: 'vault'
    dnsZoneIds: [
      privateDns.outputs.zoneIds.keyVault
    ]
  }
}

module acrPe 'modules/private-endpoint.bicep' = if (networkIsolation) {
  name: 'pe-acr'
  params: {
    location: location
    tags: tags
    name: 'pe-${acrName}'
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: foundry.outputs.containerRegistryId
    groupId: 'registry'
    dnsZoneIds: [
      privateDns.outputs.zoneIds.acr
    ]
  }
}

// Foundry standard agent setup (BYO Cosmos/Storage/Search): connections + capability host after PEs/DNS exist.
module foundryAgentByo 'modules/foundry-agent-byo.bicep' = if (networkIsolation) {
  name: 'foundry-agent-byo'
  params: {
    accountName: foundryAccountName
    projectName: foundryProjectName
    projectPrincipalId: foundry.outputs.aiProjectPrincipalId
    cosmosDbResourceId: privateFoundryDependencies.outputs.cosmosDbResourceId
    storageAccountResourceId: privateFoundryDependencies.outputs.storageAccountResourceId
    searchServiceResourceId: privateFoundryDependencies.outputs.searchServiceResourceId
  }
  dependsOn: [
    foundryPe
  ]
}

module foundryAgentByoPost 'modules/foundry-agent-byo-post.bicep' = if (networkIsolation) {
  name: 'foundry-agent-byo-post'
  params: {
    projectPrincipalId: foundry.outputs.aiProjectPrincipalId
    storageAccountResourceId: privateFoundryDependencies.outputs.storageAccountResourceId
    cosmosDbResourceId: privateFoundryDependencies.outputs.cosmosDbResourceId
    projectWorkspaceId: foundryAgentByo.outputs.projectWorkspaceId
  }
}

module containerApps 'modules/container-apps.bicep' = {
  name: 'container-apps'
  params: {
    location: location
    tags: tags
    environmentName: acaEnvName
    logAnalyticsCustomerId: monitoring.outputs.logAnalyticsCustomerId
    logAnalyticsSharedKey: monitoring.outputs.logAnalyticsSharedKey
    containerRegistryEndpoint: foundry.outputs.containerRegistryEndpoint
    containerRegistryResourceId: foundry.outputs.containerRegistryId
    domainProfile: domainProfile
    deployAgentOnAca: deployAgentOnAca
    networkIsolation: networkIsolation
    infrastructureSubnetId: networkIsolation ? network.outputs.acaSubnetId : ''
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

// Internal ACA environment: resolve its default domain from the VNet (APIM / AI Gateway backends are ACA FQDNs).
module acaPrivateDns 'modules/aca-private-dns.bicep' = if (networkIsolation) {
  name: 'aca-private-dns'
  params: {
    tags: tags
    vnetId: network.outputs.vnetId
    defaultDomain: containerApps.outputs.defaultDomain
    staticIp: containerApps.outputs.staticIp
  }
}

module gatewayApim  'modules/gateway-apimv2.bicep' = if (deployApimV2Gateway) {
  name: 'gateway-apimv2'
  params: {
    location: location
    tags: tags
    apimName: apimName
    apimSku: apimSku
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
    gatewayAppClientId: gatewayAppClientId
    foundryAccountResourceId: foundry.outputs.aiServicesId
    foundryAccountEndpoint: foundry.outputs.openAiEndpoint
    modelDeploymentName: modelDeploymentName
    catalogMcpBackendUrl: 'https://${containerApps.outputs.catalogMcpFqdn}'
    recordsApiBackendUrl: 'https://${containerApps.outputs.recordsApiFqdn}'
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    appInsightsId: monitoring.outputs.appInsightsId
    appInsightsInstrumentationKey: monitoring.outputs.appInsightsInstrumentationKey
    tokenLimitTpmPerAgent: tokenLimitTpmPerAgent
    enableContentSafety: enableContentSafety
    enableLlmMessageLogging: enableLlmMessageLogging
    networkIsolation: networkIsolation
    apimSubnetId: networkIsolation ? network.outputs.apimSubnetId : ''
  }
}

module gatewayAi 'modules/gateway-aigateway.bicep' = if (deployAiGatewayTier) {
  name: 'gateway-aigateway'
  params: {
    location: aiGatewayTierLocation
    tags: tags
    gatewayName: aiGatewayName
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
    foundryEndpoint: foundry.outputs.aiServicesEndpoint
    foundryAccountResourceId: foundry.outputs.aiServicesId
    modelDeploymentResourceId: foundry.outputs.modelDeploymentId
    modelDeploymentName: modelDeploymentName
    modelName: modelName
    modelVersion: modelVersion
    tokenLimitTpmPerAgent: tokenLimitTpmPerAgent
    requestLimitRpm: aigwRequestLimitRpm
    enableContentSafety: enableContentSafety
    catalogMcpBackendUrl: 'https://${containerApps.outputs.catalogMcpFqdn}/mcp'
    recordsApiBackendUrl: 'https://${containerApps.outputs.recordsApiFqdn}'
    appInsightsId: monitoring.outputs.appInsightsId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    keyVaultName: keyvault.outputs.keyVaultName
    runtimeKeySecretName: aigwRuntimeKeySecretName
    networkIsolation: aigwOutboundIntegration
    outboundSubnetId: aigwOutboundIntegration ? network.outputs.aigwSubnetId : ''
  }
}

// APIM Standard v2 / Premium v2 inbound private endpoint (Gateway group). Public access is left Enabled because it can
// only be disabled after the PE exists; the post-provision hook prints the lockdown step.
module apimPe 'modules/private-endpoint.bicep' = if (networkIsolation && deployApimV2Gateway) {
  name: 'pe-apim'
  params: {
    location: location
    tags: tags
    name: 'pe-${apimName}'
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: gatewayApim.outputs.apimResourceId
    groupId: 'Gateway'
    dnsZoneIds: [
      privateDns.outputs.zoneIds.apim
    ]
  }
}

// AI Gateway tier inbound Private Link (preview): same Gateway group; cannot be proven by what-if.
module aigwPe 'modules/private-endpoint.bicep' = if (networkIsolation && deployAiGatewayTier && aigwInboundPrivateEndpoint) {
  name: 'pe-aigw'
  params: {
    location: location
    tags: tags
    name: 'pe-${aiGatewayName}'
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: gatewayAi.outputs.gatewayResourceId
    groupId: 'Gateway'
    dnsZoneIds: [
      privateDns.outputs.zoneIds.apim
    ]
  }
}

var activeGatewayName = deployApimV2Gateway ? gatewayApim.outputs.apimName : gatewayAi.outputs.gatewayName
var activeGatewayUrl = deployApimV2Gateway ? gatewayApim.outputs.gatewayUrl : gatewayAi.outputs.gatewayUrl
var aigwGatewayUrl = deployAiGatewayTier ? gatewayAi.outputs.gatewayUrl : ''
var aigwMcpCatalogUrl = empty(aigwGatewayUrl) ? '' : '${aigwGatewayUrl}/default/toolservers/catalog-mcp/mcp'
var aigwMcpRecordsUrl = empty(aigwGatewayUrl) ? '' : '${aigwGatewayUrl}/default/toolservers/records/mcp'
var mcpCatalogUrl = deployApimV2Gateway ? '${activeGatewayUrl}/catalog-mcp/mcp' : aigwMcpCatalogUrl
var mcpRecordsUrl = deployApimV2Gateway ? '${activeGatewayUrl}/records-mcp/mcp' : aigwMcpRecordsUrl
var recordsApiUrl = deployApimV2Gateway ? '${activeGatewayUrl}/records' : ''

module demoConsole 'modules/demo-console.bicep' = {
  name: 'demo-console'
  params: {
    location: location
    tags: tags
    environmentId: containerApps.outputs.environmentId
    defaultDomain: containerApps.outputs.defaultDomain
    pullIdentityId: containerApps.outputs.pullIdentityId
    registryEndpoint: foundry.outputs.containerRegistryEndpoint
    tenantId: tenantId
    clientId: demoConsoleClientId
    allowedUserId: demoConsoleAllowedUserId
    clientSecret: demoConsoleClientSecret
    domainProfile: domainProfile
    agentDefaultGateway: agentDefaultGateway
    foundryAccountName: foundry.outputs.aiServicesName
    foundryProjectName: foundry.outputs.aiProjectName
    foundryProjectEndpoint: foundry.outputs.projectEndpoint
    apimGatewayUrl: deployApimV2Gateway ? gatewayApim.outputs.gatewayUrl : ''
    aigwGatewayUrl: aigwGatewayUrl
    aiGatewayMode: aiGatewayMode
    modelDeploymentName: modelDeploymentName
    workspaceName: monitoring.outputs.logAnalyticsWorkspaceName
    workspaceCustomerId: monitoring.outputs.logAnalyticsCustomerId
    keyVaultName: keyvault.outputs.keyVaultName
    keyVaultUri: keyvault.outputs.keyVaultUri
    runtimeKeySecretName: aigwRuntimeKeySecretName
    keyDelivery: aigwKeyDelivery
    runtimeKey: deployAiGatewayTier && aigwKeyDelivery == 'env' ? gatewayAi.outputs.runtimeKey : ''
  }
}

resource keyVaultForRbac 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource projectKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVaultForRbac
  name: guid(keyVaultName, foundryProjectName, keyVaultSecretsUserRoleId)
  properties: {
    principalId: foundry.outputs.aiProjectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
  }
  dependsOn: [
    keyvault
  ]
}

resource operatorKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: keyVaultForRbac
  name: guid(keyVaultName, principalId, keyVaultSecretsUserRoleId)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
  }
  dependsOn: [
    keyvault
  ]
}

module diagnostics 'modules/diagnostics.bicep' = {
  name: 'diagnostics'
  params: {
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    apimResourceId: deployApimV2Gateway ? gatewayApim.outputs.apimResourceId : gatewayAi.outputs.gatewayResourceId
    foundryAccountResourceId: foundry.outputs.aiServicesId
    foundryProjectResourceId: foundry.outputs.aiProjectResourceId
    keyVaultResourceId: keyvault.outputs.keyVaultId
    acrResourceId: foundry.outputs.containerRegistryId
  }
}

module workbook 'modules/workbook.bicep' = {
  name: 'workbook'
  params: {
    location: location
    tags: tags
    workbookDisplayName: 'Hosted agents gateway audit - ${environmentName}'
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
  }
}

module querypack 'modules/querypack.bicep' = {
  name: 'querypack'
  params: {
    location: location
    tags: tags
    queryPackName: take('queries-${normalized}-${shortSuffix}', 63)
  }
}

module alerts 'modules/alerts.bicep' = if (enableAlerts) {
  name: 'alerts'
  params: {
    location: location
    tags: tags
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    alertEmail: alertEmail
    enableEntraDiagnostics: enableEntraDiagnostics
  }
}

module sentinel 'modules/sentinel.bicep' = if (enableSentinel) {
  name: 'sentinel'
  params: {
    logAnalyticsWorkspaceName: monitoring.outputs.logAnalyticsWorkspaceName
  }
}

module activityLog 'modules/activity-log.bicep' = if (enableActivityLogExport) {
  name: 'activity-log-export'
  scope: subscription(subscriptionId)
  params: {
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
  }
}

output FOUNDRY_ACCOUNT_NAME string = foundry.outputs.aiServicesName
output FOUNDRY_PROJECT_NAME string = foundry.outputs.aiProjectName
output FOUNDRY_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
output AZURE_AI_PROJECT_ID string = foundry.outputs.aiProjectResourceId
output AZURE_AI_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
output MODEL_DEPLOYMENT_NAME string = modelDeploymentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = foundry.outputs.containerRegistryEndpoint
output CONTAINER_APPS_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output APIM_NAME string = activeGatewayName
output APIM_GATEWAY_URL string = activeGatewayUrl
output AI_GATEWAY_MODE string = aiGatewayMode
output AIGW_GATEWAY_NAME string = deployAiGatewayTier ? gatewayAi.outputs.gatewayName : ''
output AIGW_GATEWAY_URL string = aigwGatewayUrl
output AIGW_LOCATION string = deployAiGatewayTier ? aiGatewayTierLocation : ''
output AIGW_MCP_CATALOG_URL string = aigwMcpCatalogUrl
output AIGW_MCP_RECORDS_URL string = aigwMcpRecordsUrl
output LLM_API_PATH string = llmApiPath
output MCP_CATALOG_URL string = mcpCatalogUrl
output MCP_RECORDS_URL string = mcpRecordsUrl
output RECORDS_API_URL string = recordsApiUrl
output GATEWAY_APP_CLIENT_ID string = gatewayAppClientId
output LOG_ANALYTICS_WORKSPACE_ID string = monitoring.outputs.logAnalyticsWorkspaceId
output LOG_ANALYTICS_CUSTOMER_ID string = monitoring.outputs.logAnalyticsCustomerId
output APPLICATIONINSIGHTS_NAME string = monitoring.outputs.appInsightsName
@secure()
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.appInsightsConnectionString
output WORKBOOK_ID string = workbook.outputs.workbookId
output QUERY_PACK_ID string = querypack.outputs.queryPackId
output KEY_VAULT_NAME string = keyvault.outputs.keyVaultName
output KEY_VAULT_URI string = keyvault.outputs.keyVaultUri
output AIGW_RUNTIME_KEY_SECRET_NAME string = aigwRuntimeKeySecretName
output VNET_ID string = networkIsolation ? network.outputs.vnetId : ''
output ACR_NAME string = acrName
output DEMO_CONSOLE_URL string = demoConsole.outputs.url
output DEMO_CONSOLE_APP_NAME string = demoConsole.outputs.appName
