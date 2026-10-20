// AI Gateway tier (Azure API Management AI Gateway, preview).
// VERIFIED live (2026-10): the working control-plane shape is Microsoft.ApiManagement/service with sku.name 'AIGateway'
// at api-version 2025-09-01-preview. Microsoft.ApiManagement/aigateways (2026-05-01 and 2025-09-01-preview) is registered
// but returns 400 NoAvailableScaleGroups on current subscriptions, so it is intentionally NOT used.
// The gateway's child resources (workspaces/default/...) are not indexed in public Bicep types yet, so BCP081 warnings are expected.
param location string
param tags object = {}
param gatewayName string
param publisherEmail string
param publisherName string = 'Demo Publisher'
param foundryEndpoint string
param foundryAccountResourceId string
param modelDeploymentResourceId string
param modelDeploymentName string
param modelName string
param modelVersion string
param tokenLimitTpmPerAgent int
param requestLimitRpm int = 120
param enableContentSafety bool
param catalogMcpBackendUrl string
param recordsApiBackendUrl string
param appInsightsId string
@description('Log Analytics workspace resource id for gateway diagnostic logs (GatewayLogs, GatewayLlmLogs, GatewayMCPLogs).')
param logAnalyticsWorkspaceId string
@secure()
param appInsightsConnectionString string
param keyVaultName string
param runtimeKeySecretName string = 'aigw-runtime-key'
@description('When true, enable outbound VNet integration so the gateway reaches the private Foundry account and private Container Apps backends.')
param networkIsolation bool = false
param outboundSubnetId string = ''

var apiVersion = '2025-09-01-preview'
var foundryUserRoleDefinitionId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var toolCallerHeaderValue = 'aigw-runtime-key:agents'
var foundryAccountName = last(split(foundryAccountResourceId, '/'))
var runtimeKeyName = 'agents'

// Policies are inline `properties.policies[]` objects on a model alias / tool server (not APIM XML).
var requestRatePolicy = {
  type: 'requestRateLimit'
  callsPerPeriod: requestLimitRpm
  periodSeconds: 60
  counterKey: [
    'identity'
  ]
}
var tokenLimitPolicy = {
  type: 'tokenLimit'
  count: tokenLimitTpmPerAgent
  period: 'minute'
  counterKey: [
    'identity'
  ]
}
// Severity values: None | Low | Medium | High (Low = strictest block threshold).
var contentSafetyPolicy = {
  type: 'contentSafety'
  hateSeverity: 'Medium'
  violenceSeverity: 'Medium'
  sexualSeverity: 'Medium'
  selfHarmSeverity: 'Medium'
}
var modelPolicies = enableContentSafety ? [
  tokenLimitPolicy
  requestRatePolicy
  contentSafetyPolicy
] : [
  tokenLimitPolicy
  requestRatePolicy
]
var toolPolicies = enableContentSafety ? [
  requestRatePolicy
  contentSafetyPolicy
] : [
  requestRatePolicy
]

// The records-api OpenAPI spec has no `servers`; the gateway requires an absolute server URL, so inject the backend URL.
var recordsOpenApiSpec = union(loadJsonContent('../../src/records-api/openapi.json'), {
  servers: [
    {
      url: recordsApiBackendUrl
    }
  ]
})
var toolCallerCredentials = {
  type: 'header'
  headers: {
    'x-gw-caller': [
      toolCallerHeaderValue
    ]
  }
}

resource aiGateway 'Microsoft.ApiManagement/service@2025-09-01-preview' = {
  name: gatewayName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'AIGateway'
    capacity: 1
  }
  properties: union({
    publisherEmail: publisherEmail
    publisherName: publisherName
  }, networkIsolation ? {
    // Verified AIGateway networking shape (untyped, BCP037 expected): outbound integration only; inbound stays
    // public unless the Gateway private endpoint is created and public access is then disabled (see docs/10).
    virtualNetworkType: 'External'
    virtualNetworkConfiguration: {
      subnetResourceId: outboundSubnetId
    }
    publicNetworkAccess: 'Enabled'
  } : {})
}

resource gatewayDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'aigw-resource-logs'
  scope: aiGateway
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      { category: 'GatewayLogs', enabled: true }
      { category: 'GatewayLlmLogs', enabled: true }
      { category: 'GatewayMCPLogs', enabled: true }
      { category: 'WebSocketConnectionLogs', enabled: true }
      { category: 'DeveloperPortalAuditLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource foundryUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundryAccount
  name: guid(foundryAccountResourceId, aiGateway.id, foundryUserRoleDefinitionId)
  properties: {
    principalId: aiGateway.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleDefinitionId)
  }
}

// `default` workspace is created with the gateway.
resource workspace 'Microsoft.ApiManagement/service/workspaces@2025-09-01-preview' existing = {
  parent: aiGateway
  name: 'default'
}

// Requires the connectionString in addition to resourceId (verified: 400 "connectionString is required" otherwise).
resource telemetryExporter 'Microsoft.ApiManagement/service/workspaces/telemetryExporters@2025-09-01-preview' = {
  parent: workspace
  name: 'appinsights'
  properties: {
    kind: 'applicationInsights'
    payloadCapture: false
    applicationInsights: {
      resourceId: appInsightsId
      connectionString: appInsightsConnectionString
    }
  }
}

resource foundryProvider 'Microsoft.ApiManagement/service/workspaces/modelProviders@2025-09-01-preview' = {
  parent: workspace
  name: 'foundry'
  properties: {
    kind: 'Foundry'
    displayName: 'Microsoft Foundry'
    description: 'Managed identity connection to the Microsoft Foundry account backing the demo model deployment.'
    foundry: {
      endpoint: endsWith(foundryEndpoint, '/') ? foundryEndpoint : '${foundryEndpoint}/'
      resourceIds: [
        foundryAccountResourceId
      ]
      authentication: {
        kind: 'ManagedIdentity'
        managedIdentity: {
          resource: 'https://cognitiveservices.azure.com/'
        }
      }
    }
  }
  dependsOn: [
    foundryUserAssignment
  ]
}

// supportedEndpoints are relative paths (verified); they map to <gatewayUrl>/default/models<path>.
resource providerModel 'Microsoft.ApiManagement/service/workspaces/modelProviders/models@2025-09-01-preview' = {
  parent: foundryProvider
  name: modelDeploymentName
  properties: {
    displayName: modelDeploymentName
    deployment: {
      resourceId: modelDeploymentResourceId
      // Live-verified: the gateway sends this value as the upstream deployment name, so it must equal the Foundry deployment name (not the base model name) or calls return DeploymentNotFound.
      modelName: modelDeploymentName
      modelVersion: modelVersion
    }
    supportedEndpoints: [
      '/openai/v1/chat/completions'
      '/openai/v1/responses'
    ]
  }
}

// Runtime callers must reference an ALIAS in the request `model` field (an unaliased model returns 404 model_not_found).
resource modelAlias 'Microsoft.ApiManagement/service/workspaces/aliases@2025-09-01-preview' = {
  parent: workspace
  name: modelDeploymentName
  properties: {
    backendModels: [
      {
        resourceId: providerModel.id
      }
    ]
    policies: modelPolicies
  }
}

resource catalogToolServer 'Microsoft.ApiManagement/service/workspaces/toolServers@2025-09-01-preview' = {
  parent: workspace
  name: 'catalog-mcp'
  properties: {
    displayName: 'Catalog MCP'
    description: 'Remote streamable HTTP MCP endpoint for catalog tools.'
    type: 'mcp'
    endpoints: [
      {
        namespace: 'catalog'
        kind: 'mcp'
        mcp: {
          url: catalogMcpBackendUrl
          transport: 'streamableHttp'
        }
        credentials: toolCallerCredentials
      }
    ]
    policies: toolPolicies
  }
}

resource recordsToolServer 'Microsoft.ApiManagement/service/workspaces/toolServers@2025-09-01-preview' = {
  parent: workspace
  name: 'records'
  properties: {
    displayName: 'Records'
    description: 'OpenAPI-generated MCP tool server for records-api operations.'
    type: 'mcp'
    endpoints: [
      {
        namespace: 'records'
        kind: 'openApi'
        openApi: {
          specSource: {
            type: 'inline'
            contentBase64: base64(string(recordsOpenApiSpec))
          }
        }
        credentials: toolCallerCredentials
      }
    ]
    policies: toolPolicies
  }
}

// A built-in all-access key named `master` always exists; `agents` is the consumer key stored in Key Vault.
resource runtimeAccessKey 'Microsoft.ApiManagement/service/apiKeys@2025-09-01-preview' = {
  parent: aiGateway
  name: runtimeKeyName
  properties: {
    displayName: 'Hosted agents runtime key'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource runtimeKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: runtimeKeySecretName
  properties: {
    value: listSecrets('${aiGateway.id}/apiKeys/${runtimeKeyName}', apiVersion).primaryKey
  }
  dependsOn: [
    runtimeAccessKey
  ]
}

output gatewayName string = aiGateway.name
output gatewayResourceId string = aiGateway.id
output principalId string = aiGateway.identity.principalId
output gatewayUrl string = aiGateway.properties.gatewayUrl
output location string = location
output catalogMcpUrl string = '${aiGateway.properties.gatewayUrl}/default/toolservers/${catalogToolServer.name}/mcp'
output recordsMcpUrl string = '${aiGateway.properties.gatewayUrl}/default/toolservers/${recordsToolServer.name}/mcp'
output modelBaseUrl string = '${aiGateway.properties.gatewayUrl}/default/models/openai/v1'
output runtimeKeyResourceId string = runtimeAccessKey.id
@secure()
output runtimeKey string = listSecrets('${aiGateway.id}/apiKeys/${runtimeKeyName}', apiVersion).primaryKey
output runtimeKeySecretName string = runtimeKeySecretName
output keyVaultName string = keyVaultName
output keyVaultSecretUri string = runtimeKeySecret.properties.secretUri
output apiVersionUsed string = apiVersion
