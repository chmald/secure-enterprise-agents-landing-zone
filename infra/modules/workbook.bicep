// Workbook layout and query-pack panels share the same saved KQL sources.
param location string
param tags object = {}
param workbookDisplayName string
param logAnalyticsWorkspaceId string
param aigwPrincipalId string = ''

// Scope source rows before aggregation, joins, hourly bins and row limits.
func scopeQueryToTimeRange(query string, tables string[], principalId string) string => '${join(map(filter(tables, tableName => contains(query, tableName)), tableName => 'let ${tableName} = ${tableName} | where TimeGenerated {TimeRange:query};'), '\n')}\n${replace(query, 'let aigwPrincipalId = "";', 'let aigwPrincipalId = "${principalId}";')}'

// Segmented charts use one numeric measure; make-series preserves the selected window.
func tokenTrend(query string) string => concat(
  replace(query, 'bin(TimeGenerated, 1h)', 'bin_at(TimeGenerated, {TimeRange:grain}, {TimeRange:start})'),
  '\n',
  '''
| extend Series=pack_array(strcat(Group, " / input"), strcat(Group, " / output")), Tokens=pack_array(InputTokens, OutputTokens)
| mv-expand Series to typeof(string), Tokens to typeof(long)
| make-series Tokens=sum(Tokens) default=0 on TimeGenerated from {TimeRange:start} to {TimeRange:end} step {TimeRange:grain} by Series
| take 200
| mv-expand TimeGenerated to typeof(datetime), Tokens to typeof(long)
| project TimeGenerated, Tokens, Series
| order by TimeGenerated asc, Series asc
'''
)

var layout = loadJsonContent('../monitoring/workbook.json')
var sourceTables = [
  'ApiManagementGatewayLogs'
  'ApiManagementGatewayLlmLog'
  'ApiManagementGatewayMCPLog'
  'AppRequests'
  'AppDependencies'
  'AppTraces'
  'AppGenAIContent'
  'ContainerAppConsoleLogs_CL'
  'AADServicePrincipalSignInLogs'
  'AADManagedIdentitySignInLogs'
  'AuditLogs'
  'AzureActivity'
  'AzureDiagnostics'
  'ContainerRegistryLoginEvents'
  'ContainerRegistryRepositoryEvents'
]
var savedQueries = {
  'who-called-which-tool': loadTextContent('../monitoring/queries/01-who-called-which-tool.kql')
  'token-usage': loadTextContent('../monitoring/queries/02-token-usage-by-agent-and-user.kql')
  'denied-throttled': loadTextContent('../monitoring/queries/03-denied-and-throttled-requests.kql')
  'trace-lookup': replace(loadTextContent('../monitoring/queries/04-end-to-end-trace.kql'), 'declare query_parameters(traceId:string = "");', 'let traceId = "{traceId:escapejson}";')
  'tool-calls': loadTextContent('../monitoring/queries/05-mcp-tool-calls.kql')
  'llm-sample': loadTextContent('../monitoring/queries/06-llm-prompts-and-completions.kql')
  'identity-sign-ins': loadTextContent('../monitoring/queries/07-agent-identity-sign-ins.kql')
  'control-plane-changes': loadTextContent('../monitoring/queries/08-control-plane-changes.kql')
  'content-safety': loadTextContent('../monitoring/queries/09-content-safety-blocks.kql')
  'foundry-audit': loadTextContent('../monitoring/queries/10-foundry-audit.kql')
  'standard-v2-vs-aigw-tier': loadTextContent('../monitoring/queries/11-ai-gateway-tier-telemetry.kql')
  'gateway-token-trend': tokenTrend('${loadTextContent('../monitoring/queries/11-ai-gateway-tier-telemetry.kql')}\n| where Gateway in ("apim-standard-v2", "aigateway-tier") and Surface == "llm"\n| project TimeGenerated, Group=iff(Gateway == "aigateway-tier", "AI Gateway - Foundry-observed", "APIM v2"), InputTokens, OutputTokens')
  'agent-token-trend': tokenTrend('${loadTextContent('../monitoring/queries/11-ai-gateway-tier-telemetry.kql')}\n| where Gateway startswith "hosted-agent:" and Surface == "chat"\n| project TimeGenerated, Group=replace_string(Gateway, "hosted-agent:", ""), InputTokens, OutputTokens')
}
var items = [for item in layout.items: union(item, {
  content: union(item.content, item.type == 3 ? {
    crossComponentResources: [
      logAnalyticsWorkspaceId
    ]
    query: scopeQueryToTimeRange(
      contains(savedQueries, item.name)
        ? (endsWith(item.name, '-token-trend') ? savedQueries[item.name] : '${savedQueries[item.name]}\n| take 200')
        : item.content.query,
      sourceTables,
      aigwPrincipalId
    )
  } : {})
})]
var workbookData = union(layout, {
  items: items
  fallbackResourceIds: [
    logAnalyticsWorkspaceId
  ]
})

resource workbook 'Microsoft.Insights/workbooks@2022-04-01' = {
  name: guid(resourceGroup().id, workbookDisplayName)
  location: location
  tags: tags
  kind: 'shared'
  properties: {
    displayName: workbookDisplayName
    category: 'workbook'
    sourceId: logAnalyticsWorkspaceId
    serializedData: string(workbookData)
    version: 'Notebook/1.0'
  }
}

output workbookId string = workbook.id
