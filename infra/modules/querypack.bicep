// Log Analytics query pack with saved KQL for the monitoring and audit plane.
param location string
param tags object = {}
param queryPackName string
param aigwPrincipalId string = ''

resource queryPack 'Microsoft.OperationalInsights/queryPacks@2019-09-01' = {
  name: queryPackName
  location: location
  tags: tags
  properties: {}
}

var queries = [
  {
    name: '01-who-called-which-tool'
    displayName: '01 - who called which tool'
    body: loadTextContent('../monitoring/queries/01-who-called-which-tool.kql')
  }
  {
    name: '02-token-usage-by-agent-and-user'
    displayName: '02 - token usage by agent and user'
    body: loadTextContent('../monitoring/queries/02-token-usage-by-agent-and-user.kql')
  }
  {
    name: '03-denied-and-throttled-requests'
    displayName: '03 - denied and throttled requests'
    body: loadTextContent('../monitoring/queries/03-denied-and-throttled-requests.kql')
  }
  {
    name: '04-end-to-end-trace'
    displayName: '04 - end to end trace'
    body: loadTextContent('../monitoring/queries/04-end-to-end-trace.kql')
  }
  {
    name: '05-mcp-tool-calls'
    displayName: '05 - MCP tool calls'
    body: loadTextContent('../monitoring/queries/05-mcp-tool-calls.kql')
  }
  {
    name: '06-llm-prompts-and-completions'
    displayName: '06 - LLM prompts and completions'
    body: loadTextContent('../monitoring/queries/06-llm-prompts-and-completions.kql')
  }
  {
    name: '07-agent-identity-sign-ins'
    displayName: '07 - agent identity sign-ins'
    body: loadTextContent('../monitoring/queries/07-agent-identity-sign-ins.kql')
  }
  {
    name: '08-control-plane-changes'
    displayName: '08 - control plane changes'
    body: loadTextContent('../monitoring/queries/08-control-plane-changes.kql')
  }
  {
    name: '09-content-safety-blocks'
    displayName: '09 - content safety blocks'
    body: loadTextContent('../monitoring/queries/09-content-safety-blocks.kql')
  }
  {
    name: '10-foundry-audit'
    displayName: '10 - Foundry audit'
    body: loadTextContent('../monitoring/queries/10-foundry-audit.kql')
  }
  {
    name: '11-ai-gateway-tier-telemetry'
    displayName: '11 - AI Gateway tier telemetry'
    body: loadTextContent('../monitoring/queries/11-ai-gateway-tier-telemetry.kql')
  }
]

resource savedQueries 'Microsoft.OperationalInsights/queryPacks/queries@2019-09-01' = [for query in queries: {
  parent: queryPack
  name: guid(queryPack.id, query.name)
  properties: {
    displayName: query.displayName
    body: replace(query.body, 'let aigwPrincipalId = "";', 'let aigwPrincipalId = "${aigwPrincipalId}";')
    description: 'Saved query for hosted agents gateway audit demo.'
    related: {
      categories: [
        'applications'
        'monitor'
        'audit'
      ]
      resourceTypes: [
        'microsoft.apimanagement/service'
        'microsoft.insights/components'
        'microsoft.cognitiveservices/accounts'
      ]
    }
  }
}]

output queryPackId string = queryPack.id
