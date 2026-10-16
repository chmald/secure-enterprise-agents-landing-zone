// Subscription wrapper for Azure Developer CLI. Creates or reuses the resource group and passes every parameter to main.bicep.
targetScope = 'subscription'

@description('azd environment name. Lowercase alphanumeric plus hyphen, max 20, enforced by preprovision hook.')
param environmentName string
param location string
param subscriptionId string
param tenantId string
param principalId string
@allowed([
  'User'
  'ServicePrincipal'
])
param principalType string = 'User'
param resourceGroupName string = ''

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
param aigwSubnetPrefix string = '10.40.6.0/27'
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

var resolvedResourceGroupName = empty(resourceGroupName) ? 'rg-${environmentName}' : resourceGroupName

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resolvedResourceGroupName
  location: location
  tags: {
    demo: 'foundry-hosted-agents-ai-gateway-landing-zone'
    environment: environmentName
  }
}

module main 'main.bicep' = {
  name: 'main-${environmentName}'
  scope: rg
  params: {
    environmentName: environmentName
    location: location
    subscriptionId: subscriptionId
    tenantId: tenantId
    principalId: principalId
    principalType: principalType
    aiGatewayMode: aiGatewayMode
    aiGatewayTierLocation: aiGatewayTierLocation
    apimSku: apimSku
    apimPublisherEmail: apimPublisherEmail
    apimPublisherName: apimPublisherName
    gatewayAppClientId: gatewayAppClientId
    demoConsoleClientId: demoConsoleClientId
    demoConsoleAllowedUserId: demoConsoleAllowedUserId
    demoConsoleClientSecret: demoConsoleClientSecret
    agentDefaultGateway: agentDefaultGateway
    aigwKeyDelivery: aigwKeyDelivery
    tokenLimitTpmPerAgent: tokenLimitTpmPerAgent
    aigwRequestLimitRpm: aigwRequestLimitRpm
    aigwRuntimeKeySecretName: aigwRuntimeKeySecretName
    enableContentSafety: enableContentSafety
    enableLlmMessageLogging: enableLlmMessageLogging
    networkIsolation: networkIsolation
    vnetAddressPrefix: vnetAddressPrefix
    agentSubnetPrefix: agentSubnetPrefix
    acaSubnetPrefix: acaSubnetPrefix
    apimSubnetPrefix: apimSubnetPrefix
    peSubnetPrefix: peSubnetPrefix
    aigwSubnetPrefix: aigwSubnetPrefix
    aigwInboundPrivateEndpoint: aigwInboundPrivateEndpoint
    modelName: modelName
    modelVersion: modelVersion
    modelDeploymentName: modelDeploymentName
    modelSku: modelSku
    modelCapacity: modelCapacity
    domainProfile: domainProfile
    deployAgentOnAca: deployAgentOnAca
    seedSampleData: seedSampleData
    logRetentionDays: logRetentionDays
    enableAlerts: enableAlerts
    alertEmail: alertEmail
    enableActivityLogExport: enableActivityLogExport
    enableSentinel: enableSentinel
    enableEntraDiagnostics: enableEntraDiagnostics
  }
}

output AZURE_RESOURCE_GROUP string = rg.name
output FOUNDRY_ACCOUNT_NAME string = main.outputs.FOUNDRY_ACCOUNT_NAME
output FOUNDRY_PROJECT_NAME string = main.outputs.FOUNDRY_PROJECT_NAME
output FOUNDRY_PROJECT_ENDPOINT string = main.outputs.FOUNDRY_PROJECT_ENDPOINT
output AZURE_AI_PROJECT_ID string = main.outputs.AZURE_AI_PROJECT_ID
output AZURE_AI_PROJECT_ENDPOINT string = main.outputs.AZURE_AI_PROJECT_ENDPOINT
output MODEL_DEPLOYMENT_NAME string = main.outputs.MODEL_DEPLOYMENT_NAME
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = main.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT
output CONTAINER_APPS_ENVIRONMENT_NAME string = main.outputs.CONTAINER_APPS_ENVIRONMENT_NAME
output APIM_NAME string = main.outputs.APIM_NAME
output APIM_GATEWAY_URL string = main.outputs.APIM_GATEWAY_URL
output AI_GATEWAY_MODE string = main.outputs.AI_GATEWAY_MODE
output AIGW_GATEWAY_NAME string = main.outputs.AIGW_GATEWAY_NAME
output AIGW_GATEWAY_URL string = main.outputs.AIGW_GATEWAY_URL
output AIGW_LOCATION string = main.outputs.AIGW_LOCATION
output AIGW_MCP_CATALOG_URL string = main.outputs.AIGW_MCP_CATALOG_URL
output AIGW_MCP_RECORDS_URL string = main.outputs.AIGW_MCP_RECORDS_URL
output LLM_API_PATH string = main.outputs.LLM_API_PATH
output MCP_CATALOG_URL string = main.outputs.MCP_CATALOG_URL
output MCP_RECORDS_URL string = main.outputs.MCP_RECORDS_URL
output RECORDS_API_URL string = main.outputs.RECORDS_API_URL
output GATEWAY_APP_CLIENT_ID string = main.outputs.GATEWAY_APP_CLIENT_ID
output LOG_ANALYTICS_WORKSPACE_ID string = main.outputs.LOG_ANALYTICS_WORKSPACE_ID
output LOG_ANALYTICS_CUSTOMER_ID string = main.outputs.LOG_ANALYTICS_CUSTOMER_ID
output APPLICATIONINSIGHTS_NAME string = main.outputs.APPLICATIONINSIGHTS_NAME
@secure()
output APPLICATIONINSIGHTS_CONNECTION_STRING string = main.outputs.APPLICATIONINSIGHTS_CONNECTION_STRING
output WORKBOOK_ID string = main.outputs.WORKBOOK_ID
output QUERY_PACK_ID string = main.outputs.QUERY_PACK_ID
output KEY_VAULT_NAME string = main.outputs.KEY_VAULT_NAME
output KEY_VAULT_URI string = main.outputs.KEY_VAULT_URI
output AIGW_RUNTIME_KEY_SECRET_NAME string = main.outputs.AIGW_RUNTIME_KEY_SECRET_NAME
output VNET_ID string = main.outputs.VNET_ID
output DEMO_CONSOLE_URL string = main.outputs.DEMO_CONSOLE_URL
output DEMO_CONSOLE_APP_NAME string = main.outputs.DEMO_CONSOLE_APP_NAME
