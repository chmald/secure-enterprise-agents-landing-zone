param location string
param tags object
param environmentId string
param defaultDomain string
param pullIdentityId string
param registryEndpoint string
param tenantId string
param clientId string
param allowedUserId string
@secure()
param clientSecret string
param enableDemoObo bool = false
param oboClientId string = ''
@secure()
param oboClientSecret string = ''
param gatewayAppClientId string = ''
param domainProfile string
param agentDefaultGateway string
param foundryAccountName string
param foundryProjectName string
param foundryProjectEndpoint string
param apimGatewayUrl string
param aigwGatewayUrl string
param aigwPrincipalId string = ''
param aiGatewayMode string
param modelDeploymentName string
param workspaceName string
param workspaceCustomerId string
param workbookId string = ''
param keyVaultName string
param keyVaultUri string
param runtimeKeySecretName string
param keyDelivery string
@secure()
param runtimeKey string = ''

var appName = 'ca-demo-console'
var consoleUrl = 'https://${appName}.${defaultDomain}'

resource console 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: union(tags, {
    'azd-service-name': 'demo-console'
  })
  identity: {
    type: 'SystemAssigned,UserAssigned'
    userAssignedIdentities: {
      '${pullIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: registryEndpoint
          identity: pullIdentityId
        }
      ]
      secrets: concat([
        {
          name: 'entra-client-secret'
          value: clientSecret
        }
      ], enableDemoObo && !empty(oboClientSecret) ? [
        {
          name: 'obo-signin-secret'
          value: oboClientSecret
        }
      ] : [], keyDelivery == 'env' && !empty(runtimeKey) ? [
        {
          name: 'aigw-runtime-key'
          value: runtimeKey
        }
      ] : [])
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8080
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          name: 'demo-console'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat([
            { name: 'AZURE_TENANT_ID', value: tenantId }
            { name: 'DEMO_CONSOLE_ALLOWED_USER_ID', value: allowedUserId }
            { name: 'DEMO_CONSOLE_URL', value: consoleUrl }
            { name: 'DOMAIN_PROFILE', value: domainProfile }
            { name: 'ENABLE_DEMO_OBO', value: toLower(string(enableDemoObo)) }
            { name: 'DEMO_CONSOLE_CLIENT_ID', value: clientId }
            { name: 'DEMO_OBO_CLIENT_ID', value: oboClientId }
            { name: 'GATEWAY_APP_CLIENT_ID', value: gatewayAppClientId }
            { name: 'HOSTED_DEFAULT_GATEWAY', value: agentDefaultGateway }
            { name: 'FOUNDRY_PROJECT_ENDPOINT', value: foundryProjectEndpoint }
            { name: 'APIM_GATEWAY_URL', value: apimGatewayUrl }
            { name: 'AIGW_GATEWAY_URL', value: aigwGatewayUrl }
            { name: 'AIGW_PRINCIPAL_ID', value: aigwPrincipalId }
            { name: 'AI_GATEWAY_MODE', value: aiGatewayMode }
            { name: 'MODEL_DEPLOYMENT_NAME', value: modelDeploymentName }
            { name: 'LOG_ANALYTICS_CUSTOMER_ID', value: workspaceCustomerId }
            { name: 'WORKBOOK_ID', value: workbookId }
            { name: 'KEY_VAULT_URI', value: keyVaultUri }
            { name: 'AIGW_RUNTIME_KEY_SECRET_NAME', value: runtimeKeySecretName }
            { name: 'AIGW_KEY_DELIVERY', value: keyDelivery }
          ], enableDemoObo ? [
            { name: 'DEMO_CONSOLE_CLIENT_SECRET', secretRef: 'entra-client-secret' }
            { name: 'DEMO_OBO_CLIENT_SECRET', secretRef: 'obo-signin-secret' }
          ] : [], keyDelivery == 'env' && !empty(runtimeKey) ? [
            { name: 'AIGW_RUNTIME_KEY', secretRef: 'aigw-runtime-key' }
          ] : [])
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

resource auth 'Microsoft.App/containerApps/authConfigs@2024-03-01' = {
  parent: console
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      unauthenticatedClientAction: 'RedirectToLoginPage'
      redirectToProvider: 'azureactivedirectory'
      excludedPaths: [
        '/healthz'
        '/api/identity/obo/callback'
      ]
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: clientId
          clientSecretSettingName: 'entra-client-secret'
          openIdIssuer: '${environment().authentication.loginEndpoint}${tenantId}/v2.0'
        }
        validation: {
          allowedAudiences: [
            clientId
          ]
          defaultAuthorizationPolicy: {
            allowedPrincipals: {
              identities: [
                allowedUserId
              ]
            }
          }
        }
      }
    }
    login: {
      allowedExternalRedirectUrls: [
        consoleUrl
      ]
    }
    httpSettings: {
      requireHttps: true
    }
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  parent: foundry
  name: foundryProjectName
}
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: workspaceName
}
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

var aiUserRole = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var cognitiveUserRole = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var logsReaderRole = '73c42c96-874c-492b-b04d-ab87d138a893'
var secretsUserRole = '4633458b-17de-408a-b874-0445c86b69e6'

resource projectAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: project
  name: guid(project.id, console.id, aiUserRole)
  properties: {
    principalId: console.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', aiUserRole)
  }
}
resource gatewayTokenAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundry
  name: guid(foundry.id, console.id, cognitiveUserRole)
  properties: {
    principalId: console.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveUserRole)
  }
}
resource logsAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: workspace
  name: guid(workspace.id, console.id, logsReaderRole)
  properties: {
    principalId: console.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', logsReaderRole)
  }
}
resource keyAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aigwGatewayUrl) && keyDelivery == 'keyvault') {
  scope: vault
  name: guid(vault.id, console.id, secretsUserRole)
  properties: {
    principalId: console.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRole)
  }
}

output url string = consoleUrl
output appName string = console.name
