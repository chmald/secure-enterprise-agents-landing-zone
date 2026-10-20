// APIM v2 gateway mode: LLM API, native MCP passthrough, REST API, REST-as-MCP, products, policies, and diagnostics.
param location string
param tags object = {}
param apimName string
@allowed([
  'StandardV2'
  'PremiumV2'
])
param apimSku string = 'StandardV2'
param publisherEmail string
param publisherName string
param gatewayAppClientId string
param foundryAccountResourceId string
param foundryAccountEndpoint string
param modelDeploymentName string
param catalogMcpBackendUrl string
param recordsApiBackendUrl string
param logAnalyticsWorkspaceId string
param appInsightsId string
@secure()
param appInsightsInstrumentationKey string
param tokenLimitTpmPerAgent int
param enableContentSafety bool
param enableLlmMessageLogging bool
param networkIsolation bool = false
param apimSubnetId string = ''

var gatewayAudience = 'api://${gatewayAppClientId}'
var llmApiPath = 'llm'
var apiVersion = '2025-09-01-preview'
var normalizedFoundryAccountEndpoint = endsWith(foundryAccountEndpoint, '/') ? substring(foundryAccountEndpoint, 0, length(foundryAccountEndpoint) - 1) : foundryAccountEndpoint
var foundryOpenAiV1BackendUrl = '${normalizedFoundryAccountEndpoint}/openai/v1'
var llmPolicyXml = replace(replace(replace(replace(replace(loadTextContent('../policies/llm-api-policy.xml'), '{{gateway-audience}}', gatewayAudience), '{{gateway-client-id}}', gatewayAppClientId), '{{token-limit-tpm-per-agent}}', string(tokenLimitTpmPerAgent)), '{{enable-content-safety}}', string(enableContentSafety)), '{{model-deployment-name}}', modelDeploymentName)
var mcpPolicyXml = replace(replace(loadTextContent('../policies/mcp-api-policy.xml'), '{{gateway-audience}}', gatewayAudience), '{{gateway-client-id}}', gatewayAppClientId)
var recordsPolicyXml = replace(replace(loadTextContent('../policies/records-api-policy.xml'), '{{gateway-audience}}', gatewayAudience), '{{gateway-client-id}}', gatewayAppClientId)
var identityFragmentXml = loadTextContent('../policies/fragments/identity-headers.xml')

resource apim 'Microsoft.ApiManagement/service@2025-09-01-preview' = {
  name: apimName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: apimSku
    capacity: 1
  }
  properties: union({
    publisherEmail: publisherEmail
    publisherName: publisherName
    publicNetworkAccess: 'Enabled'
  }, networkIsolation ? {
    virtualNetworkConfiguration: {
      subnetResourceId: apimSubnetId
    }
  } : {})
}

resource globalDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'apim-resource-logs'
  scope: apim
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        category: 'GatewayLogs'
        enabled: true
      }
      {
        category: 'GatewayLlmLogs'
        enabled: true
      }
      {
        category: 'GatewayMCPLogs'
        enabled: true
      }
      {
        category: 'WebSocketConnectionLogs'
        enabled: true
      }
      {
        category: 'DeveloperPortalAuditLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

resource azureMonitorLogger 'Microsoft.ApiManagement/service/loggers@2024-06-01-preview' = {
  parent: apim
  name: 'azuremonitor'
  properties: {
    loggerType: 'azureMonitor'
    isBuffered: false
  }
}

resource appInsightsLogger 'Microsoft.ApiManagement/service/loggers@2021-12-01-preview' = if (!empty(appInsightsId) && !empty(appInsightsInstrumentationKey)) {
  parent: apim
  name: 'appinsights-logger'
  properties: {
    credentials: {
      instrumentationKey: appInsightsInstrumentationKey
    }
    loggerType: 'applicationInsights'
    resourceId: appInsightsId
    isBuffered: false
  }
}

resource identityFragment 'Microsoft.ApiManagement/service/policyFragments@2024-06-01-preview' = {
  parent: apim
  name: 'identity-headers'
  properties: {
    description: 'Strip client x-gw-* headers and stamp gateway-derived identity headers.'
    format: 'rawxml'
    value: identityFragmentXml
  }
}

resource starterProduct 'Microsoft.ApiManagement/service/products@2025-09-01-preview' = {
  parent: apim
  name: 'hosted-agent-gateway'
  properties: {
    displayName: 'Hosted agent gateway'
    description: 'Entitlement product for the hosted-agent demo gateway.'
    subscriptionRequired: true
    approvalRequired: false
    state: 'published'
  }
}

resource demoSubscription 'Microsoft.ApiManagement/service/subscriptions@2025-09-01-preview' = {
  parent: apim
  name: 'hosted-agent-demo'
  properties: {
    displayName: 'Hosted agent demo subscription'
    scope: '/products/${starterProduct.name}'
    state: 'active'
    allowTracing: true
  }
}

resource foundryBackend 'Microsoft.ApiManagement/service/backends@2025-09-01-preview' = {
  parent: apim
  name: 'foundry-openai-v1'
  properties: {
    protocol: 'http'
    url: foundryOpenAiV1BackendUrl
    type: 'Single'
    credentials: {
      #disable-next-line BCP037
      managedIdentity: {
        resource: 'https://cognitiveservices.azure.com'
      }
    }
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
    circuitBreaker: {
      rules: [
        {
          name: 'foundry-429-5xx'
          failureCondition: {
            count: 3
            interval: 'PT1M'
            statusCodeRanges: [
              {
                min: 429
                max: 429
              }
              {
                min: 500
                max: 599
              }
            ]
          }
          tripDuration: 'PT1M'
          acceptRetryAfter: true
        }
      ]
    }
  }
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: last(split(foundryAccountResourceId, '/'))
}

var cognitiveServicesUserRoleDefinitionId = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var cognitiveServicesOpenAIUserRoleDefinitionId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource apimAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundryAccount
  name: guid(foundryAccountResourceId, apim.id, cognitiveServicesUserRoleDefinitionId)
  properties: {
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleDefinitionId)
  }
}

resource apimOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundryAccount
  name: guid(foundryAccountResourceId, apim.id, cognitiveServicesOpenAIUserRoleDefinitionId)
  properties: {
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleDefinitionId)
  }
}

resource catalogBackend 'Microsoft.ApiManagement/service/backends@2025-09-01-preview' = {
  parent: apim
  name: 'catalog-mcp-backend'
  properties: {
    protocol: 'http'
    url: '${catalogMcpBackendUrl}/mcp'
    type: 'Single'
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
  }
}

resource recordsBackend 'Microsoft.ApiManagement/service/backends@2025-09-01-preview' = {
  parent: apim
  name: 'records-api-backend'
  properties: {
    protocol: 'http'
    url: recordsApiBackendUrl
    type: 'Single'
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
  }
}

resource llmApi 'Microsoft.ApiManagement/service/apis@2025-09-01-preview' = {
  parent: apim
  name: 'llm-openai-v1'
  properties: {
    type: 'http'
    apiType: 'http'
    displayName: 'LLM OpenAI-compatible API'
    description: 'OpenAI-compatible v1 path routed to the Microsoft Foundry account backend using APIM managed identity.'
    path: '${llmApiPath}/openai/v1'
    protocols: [
      'https'
    ]
    subscriptionRequired: false
    serviceUrl: foundryOpenAiV1BackendUrl
  }
}

resource llmApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2025-09-01-preview' = {
  parent: llmApi
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: llmPolicyXml
  }
  dependsOn: [
    identityFragment
  ]
}

resource llmResponsesOperation 'Microsoft.ApiManagement/service/apis/operations@2025-09-01-preview' = {
  parent: llmApi
  name: 'responses'
  properties: {
    displayName: 'OpenAI Responses'
    method: 'POST'
    urlTemplate: '/responses'
    responses: [
      {
        statusCode: 200
        description: 'OK'
      }
    ]
  }
}

resource llmChatCompletionsOperation 'Microsoft.ApiManagement/service/apis/operations@2025-09-01-preview' = {
  parent: llmApi
  name: 'chat-completions'
  properties: {
    displayName: 'OpenAI Chat Completions'
    method: 'POST'
    urlTemplate: '/chat/completions'
    responses: [
      {
        statusCode: 200
        description: 'OK'
      }
    ]
  }
}

resource llmDiagnostics 'Microsoft.ApiManagement/service/apis/diagnostics@2024-06-01-preview' = {
  parent: llmApi
  name: 'azuremonitor'
  properties: {
    alwaysLog: 'allErrors'
    loggerId: azureMonitorLogger.id
    logClientIp: true
    metrics: true
    verbosity: 'verbose'
    sampling: {
      samplingType: 'fixed'
      percentage: json('100')
    }
    frontend: {
      request: {
        headers: []
        body: {
          bytes: 0
        }
      }
      response: {
        headers: []
        body: {
          bytes: 0
        }
      }
    }
    backend: {
      request: {
        headers: []
        body: {
          bytes: 0
        }
      }
      response: {
        headers: []
        body: {
          bytes: 0
        }
      }
    }
    largeLanguageModel: {
      logs: enableLlmMessageLogging ? 'enabled' : 'disabled'
      requests: {
        messages: enableLlmMessageLogging ? 'all' : 'none'
        maxSizeInBytes: 262144
      }
      responses: {
        messages: enableLlmMessageLogging ? 'all' : 'none'
        maxSizeInBytes: 262144
      }
    }
  }
}

resource catalogMcp 'Microsoft.ApiManagement/service/apis@2025-09-01-preview' = {
  parent: apim
  name: 'catalog-mcp'
  properties: {
    type: 'http'
    apiType: 'http'
    displayName: 'Catalog MCP Server'
    description: 'HTTP proxy for the catalog MCP Streamable HTTP endpoint.'
    path: 'catalog-mcp'
    protocols: [
      'https'
    ]
    serviceUrl: catalogMcpBackendUrl
    subscriptionRequired: false
  }
}

resource catalogMcpPostOperation 'Microsoft.ApiManagement/service/apis/operations@2025-09-01-preview' = {
  parent: catalogMcp
  name: 'mcp-post'
  properties: {
    displayName: 'MCP JSON-RPC'
    method: 'POST'
    urlTemplate: '/mcp'
    responses: [
      {
        statusCode: 200
        description: 'OK'
      }
    ]
  }
}

resource catalogMcpPolicy 'Microsoft.ApiManagement/service/apis/policies@2025-09-01-preview' = {
  parent: catalogMcp
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: mcpPolicyXml
  }
  dependsOn: [
    identityFragment
  ]
}

resource recordsRestApi 'Microsoft.ApiManagement/service/apis@2025-09-01-preview' = {
  parent: apim
  name: 'records-api'
  properties: {
    type: 'http'
    apiType: 'http'
    displayName: 'Records REST API'
    description: 'Plain REST API route for records tooling and OpenAPI-tool comparison.'
    path: 'records'
    protocols: [
      'https'
    ]
    serviceUrl: '${recordsApiBackendUrl}/records'
    subscriptionRequired: false
  }
}

resource recordsListOperation 'Microsoft.ApiManagement/service/apis/operations@2025-09-01-preview' = {
  parent: recordsRestApi
  name: 'list-records'
  properties: {
    displayName: 'List records'
    method: 'GET'
    urlTemplate: '/'
    responses: [
      {
        statusCode: 200
        description: 'OK'
      }
    ]
  }
}

resource recordsGetOperation 'Microsoft.ApiManagement/service/apis/operations@2025-09-01-preview' = {
  parent: recordsRestApi
  name: 'get-record'
  properties: {
    displayName: 'Get record'
    method: 'GET'
    urlTemplate: '/{id}'
    templateParameters: [
      {
        name: 'id'
        type: 'string'
        required: true
      }
    ]
    responses: [
      {
        statusCode: 200
        description: 'OK'
      }
    ]
  }
}

resource recordsCreateOperation 'Microsoft.ApiManagement/service/apis/operations@2025-09-01-preview' = {
  parent: recordsRestApi
  name: 'create-record'
  properties: {
    displayName: 'Create record'
    method: 'POST'
    urlTemplate: '/'
    responses: [
      {
        statusCode: 201
        description: 'Created'
      }
    ]
  }
}

resource recordsUpdateOperation 'Microsoft.ApiManagement/service/apis/operations@2025-09-01-preview' = {
  parent: recordsRestApi
  name: 'update-record'
  properties: {
    displayName: 'Update record'
    method: 'PATCH'
    urlTemplate: '/{id}'
    templateParameters: [
      {
        name: 'id'
        type: 'string'
        required: true
      }
    ]
    responses: [
      {
        statusCode: 200
        description: 'OK'
      }
    ]
  }
}

resource recordsApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2025-09-01-preview' = {
  parent: recordsRestApi
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: recordsPolicyXml
  }
  dependsOn: [
    identityFragment
  ]
}

resource recordsMcp 'Microsoft.ApiManagement/service/apis@2025-09-01-preview' = {
  parent: apim
  name: 'records-mcp'
  properties: {
    type: 'http'
    apiType: 'http'
    displayName: 'Records REST-as-MCP Server'
    description: 'HTTP proxy for the records MCP Streamable HTTP endpoint.'
    path: 'records-mcp'
    protocols: [
      'https'
    ]
    serviceUrl: recordsApiBackendUrl
    subscriptionRequired: false
  }
}

resource recordsMcpPostOperation 'Microsoft.ApiManagement/service/apis/operations@2025-09-01-preview' = {
  parent: recordsMcp
  name: 'mcp-post'
  properties: {
    displayName: 'MCP JSON-RPC'
    method: 'POST'
    urlTemplate: '/mcp'
    responses: [
      {
        statusCode: 200
        description: 'OK'
      }
    ]
  }
}

resource recordsMcpPolicy 'Microsoft.ApiManagement/service/apis/policies@2025-09-01-preview' = {
  parent: recordsMcp
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: mcpPolicyXml
  }
  dependsOn: [
    identityFragment
  ]
}

resource productBindings 'Microsoft.ApiManagement/service/products/apis@2025-09-01-preview' = [for apiName in [
  llmApi.name
  catalogMcp.name
  recordsRestApi.name
  recordsMcp.name
]: {
  parent: starterProduct
  name: apiName
}]

output apimName string = apim.name
output apimResourceId string = apim.id
output gatewayUrl string = apim.properties.gatewayUrl
output apiVersionUsed string = apiVersion
