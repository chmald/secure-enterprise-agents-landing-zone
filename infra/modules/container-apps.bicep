// Container Apps runtime for tool backends and optional same-image self-hosted agent comparison.
param location string
param tags object = {}
param environmentName string
param logAnalyticsCustomerId string
@secure()
param logAnalyticsSharedKey string
param containerRegistryEndpoint string
param containerRegistryResourceId string
param domainProfile string
param deployAgentOnAca bool = false
param networkIsolation bool = false
param infrastructureSubnetId string = ''
@secure()
param appInsightsConnectionString string

resource managedEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: union({
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }, networkIsolation ? {
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: true
    }
  } : {})
}

var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(containerRegistryResourceId, '/'))
}

// A user-assigned identity exists (and holds AcrPull) before any app is created, so a first-time deploy
// can register the ACR with an identity. A system identity cannot be granted AcrPull before the app exists.
resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${environmentName}-acrpull'
  location: location
  tags: tags
}

resource pullIdentityAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(containerRegistryResourceId, pullIdentity.id, acrPullRoleDefinitionId)
  properties: {
    principalId: pullIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleDefinitionId)
  }
}

var appIdentity = {
  type: 'SystemAssigned,UserAssigned'
  userAssignedIdentities: {
    '${pullIdentity.id}': {}
  }
}
var appRegistries = [
  {
    server: containerRegistryEndpoint
    identity: pullIdentity.id
  }
]

var placeholderImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
var commonEnv = [
  {
    name: 'DOMAIN_PROFILE'
    value: domainProfile
  }
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsightsConnectionString
  }
]

// catalog-mcp listens on 8080 to align with the code agent's PORT default.
resource catalogMcp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-catalog-mcp'
  location: location
  tags: union(tags, {
    'azd-service-name': 'catalog-mcp'
  })
  identity: appIdentity
  dependsOn: [
    pullIdentityAcrPull
  ]
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: appRegistries
      ingress: {
        external: !networkIsolation
        targetPort: 8080
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          name: 'catalog-mcp'
          image: placeholderImage
          env: concat(commonEnv, [
            {
              name: 'PORT'
              value: '8080'
            }
          ])
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// records-api listens on 8080 to align with the code agent's PORT default.
resource recordsApi 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-records-api'
  location: location
  tags: union(tags, {
    'azd-service-name': 'records-api'
  })
  identity: appIdentity
  dependsOn: [
    pullIdentityAcrPull
  ]
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: appRegistries
      ingress: {
        external: !networkIsolation
        targetPort: 8080
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          name: 'records-api'
          image: placeholderImage
          env: concat(commonEnv, [
            {
              name: 'PORT'
              value: '8080'
            }
          ])
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource hostedAgentAca 'Microsoft.App/containerApps@2024-03-01' = if (deployAgentOnAca) {
  name: 'ca-hosted-agent-compare'
  location: location
  tags: union(tags, {
    'azd-service-name': 'hosted-agent-on-aca'
  })
  identity: appIdentity
  dependsOn: [
    pullIdentityAcrPull
  ]
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: appRegistries
      ingress: {
        external: !networkIsolation
        targetPort: 8088
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          name: 'hosted-agent'
          image: placeholderImage
          env: concat(commonEnv, [
            {
              name: 'PORT'
              value: '8088'
            }
            {
              name: 'AGENT_RUNTIME'
              value: 'aca'
            }
          ])
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
}

output environmentName string = managedEnvironment.name
output environmentId string = managedEnvironment.id
output pullIdentityId string = pullIdentity.id
output defaultDomain string = managedEnvironment.properties.defaultDomain
output staticIp string = managedEnvironment.properties.staticIp
output catalogMcpFqdn string = catalogMcp.properties.configuration.ingress.fqdn
output recordsApiFqdn string = recordsApi.properties.configuration.ingress.fqdn
output hostedAgentAcaFqdn string = deployAgentOnAca ? hostedAgentAca.properties.configuration.ingress.fqdn : ''
