[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 09 Monitoring and audit

# 09 - Monitoring and audit

<p>
  <img src="./assets/icons/monitor.svg" width="40" alt="Azure Monitor"/>&nbsp;
  <img src="./assets/icons/log-analytics.svg" width="40" alt="Log Analytics"/>&nbsp;
  <img src="./assets/icons/application-insights.svg" width="40" alt="Application Insights"/>&nbsp;
  <img src="./assets/icons/workbooks.svg" width="40" alt="Workbooks"/>&nbsp;
  <img src="./assets/icons/query-pack.svg" width="40" alt="Query pack"/>&nbsp;
  <img src="./assets/icons/alerts.svg" width="40" alt="Alerts"/>&nbsp;
  <img src="./assets/icons/diagnostic-settings.svg" width="40" alt="Diagnostic settings"/>&nbsp;
  <img src="./assets/icons/activity-log.svg" width="40" alt="Activity log"/>&nbsp;
  <img src="./assets/icons/sentinel.svg" width="40" alt="Microsoft Sentinel"/>&nbsp;
  <img src="./assets/icons/defender-for-cloud.svg" width="40" alt="Defender for Cloud"/>&nbsp;
  <img src="./assets/icons/entra-id.svg" width="40" alt="Microsoft Entra ID"/>
</p>

![GA](./assets/badges/ga.svg) ![Preview](./assets/badges/preview.svg) ![Opt-in](./assets/badges/opt-in.svg) ![Live tested](./assets/badges/live-tested.svg)

This is the **audit plane** of the landing zone: how a security, compliance or platform team proves *which human, through which agent, called which tool or model, at what time, with how many tokens, and whether the gateway allowed it*. It is written for platform engineers who operate the demo and for auditors or security architects who need to see the evidence trail before they approve a hosted-agent workload.

> [!IMPORTANT]
> **The auditor's question.** *"Last Tuesday a work order was created by an agent. Which person asked for it, which agent identity acted, which gateway and tool carried the call, what did the model cost in tokens, and was any control triggered?"*
> Every section below exists to answer that one question with a join across a handful of Log Analytics tables - without logging secrets or full tool payloads.

## At a glance

| | Item | What it gives you |
|---|---|---|
| <img src="./assets/icons/log-analytics.svg" width="24" alt=""/> | **One workspace** | Gateway, container, Foundry, Key Vault, registry and (opt-in) Activity Log and Entra data land in a single Log Analytics workspace (`PerGB2018`, `LOG_RETENTION_DAYS`, default 90). |
| <img src="./assets/icons/application-insights.svg" width="24" alt=""/> | **Workspace-based Application Insights** | Agent and tool OpenTelemetry spans, plus the structured `tool_audit` record, share the same workspace. |
| <img src="./assets/icons/query-pack.svg" width="24" alt=""/> | **11 saved queries** | A query pack named `NN-slug` that answers the audit, usage, denial, trace, identity, control-plane, content-safety and Foundry questions. |
| <img src="./assets/icons/workbooks.svg" width="24" alt=""/> | **1 workbook, 17 query panels** | Two token trend charts plus all 11 saved queries, telemetry coverage, gateway latency, hosted-agent content, and Key Vault/registry audit. Seven labeled sections; optional section-specific trace input. |
| <img src="./assets/icons/alerts.svg" width="24" alt=""/> | **Up to 5 alerts** | Scheduled-query rules (severity 2) for throttling spikes, denied tools, 5xx, content-safety blocks and agent sign-in failures. |
| <img src="./assets/icons/sentinel.svg" width="24" alt=""/> | **Opt-in SIEM / CSPM path** | Microsoft Sentinel onboarding, Activity Log export and Entra diagnostics are single `azd env set` switches. |

## The audit plane

The picture below shows where each signal is produced and where it is stored. The two lanes - **gateway logs** (what the platform saw) and **application telemetry** (what the agent and tools said about themselves) - are joined on trace and correlation identifiers.

[![Monitoring and audit plane](./assets/monitoring-audit-plane.png)](./assets/monitoring-audit-plane.png)

<sub>Editable source: [`assets/monitoring-audit-plane.drawio`](./assets/monitoring-audit-plane.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

[![Trace correlation across hops](./assets/trace-correlation.png)](./assets/trace-correlation.png)

<sub>Editable source: [`assets/trace-correlation.drawio`](./assets/trace-correlation.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

> [!NOTE]
> Both pictures describe the Standard v2 path end to end. The preview AI Gateway tier emits OpenTelemetry `gen_ai.*` data to Application Insights instead of APIM resource logs, so the same question is answered with query 11 plus the tool audit record (see [AI Gateway tier telemetry](#ai-gateway-tier-telemetry-preview)).

## Sources, categories and tables

Each Azure resource sends a defined set of log categories to the workspace through a diagnostic setting. Categories are the *switch*, tables are what you query. Resource-specific tables are used where the service supports them (`logAnalyticsDestinationType: Dedicated` on API Management).

| Source | Diagnostic setting / path | Categories enabled | Tables you query | Status |
|---|---|---|---|---|
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> **API Management (Standard v2)** | `apim-resource-logs` ([monitor reference](https://learn.microsoft.com/en-us/azure/api-management/monitor-api-management-reference)) | `GatewayLogs`, `GatewayLlmLogs`, `GatewayMCPLogs`, `WebSocketConnectionLogs`, `DeveloperPortalAuditLogs` + `AllMetrics` | `ApiManagementGatewayLogs`, `ApiManagementGatewayLlmLog`, `ApiManagementGatewayMCPLog` | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/foundry.svg" width="20" alt=""/> **Foundry account** | `foundry-account-logs` | `Audit`, `RequestResponse`, `Trace`, `AzureOpenAIRequestUsage`, `ManagedNetworkEvent` + `AllMetrics` | `AzureDiagnostics` (or resource-specific tables, depending on the account's destination type) | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/foundry-project.svg" width="20" alt=""/> **Foundry project** | `foundry-project-logs` | `Audit`, `Trace` | `AzureDiagnostics` | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/container-apps-environment.svg" width="20" alt=""/> **Container Apps environment** | `appLogsConfiguration` (workspace shared key) | Console and system logs for catalog MCP, records API and the optional agent-on-ACA | `ContainerAppConsoleLogs_CL` (contains the `tool_audit` JSON lines) | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""/> **Key Vault** | `keyvault-audit` | `AuditEvent` | `AzureDiagnostics` | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/container-registry.svg" width="20" alt=""/> **Container Registry** | `acr-logs` | `ContainerRegistryLoginEvents`, `ContainerRegistryRepositoryEvents` | `ContainerRegistryLoginEvents`, `ContainerRegistryRepositoryEvents` | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/activity-log.svg" width="20" alt=""/> **Subscription Activity Log** | `modules/activity-log.bicep` ([activity log](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/activity-log)) | `Administrative`, `Security`, `Policy`, `ResourceHealth`, `Recommendation` | `AzureActivity` | ![Opt-in](./assets/badges/opt-in.svg) `ENABLE_ACTIVITY_LOG_EXPORT` |
| <img src="./assets/icons/entra-id.svg" width="20" alt=""/> **Microsoft Entra ID** | `scripts/Enable-EntraDiagnostics.ps1` (tenant level; needs a Security Administrator) | Service principal, managed identity and audit logs; agent sign-ins appear as an `agentSignIn` attribute ([Learn](https://learn.microsoft.com/en-us/entra/agent-id/sign-in-audit-logs-agents)) | `AADServicePrincipalSignInLogs`, `AADManagedIdentitySignInLogs`, `AuditLogs` | ![Opt-in](./assets/badges/opt-in.svg) `ENABLE_ENTRA_DIAGNOSTICS` |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> **AI Gateway tier** | Built-in Application Insights telemetry ([Learn](https://learn.microsoft.com/en-us/azure/api-management/genai-gateway-capabilities)) | n/a - telemetry, not a diagnostic category | `AppRequests` (`AppRoleName` `aigw-*`; tokens in `Measurements`), `AppDependencies`, `ApiManagementGatewayMCPLog`; **no** `ApiManagementGatewayLlmLog` | ![Public preview](./assets/badges/public-preview.svg) ![Live tested](./assets/badges/live-tested.svg) |
| <img src="./assets/icons/application-insights.svg" width="20" alt=""/> **Hosted agents and tools** | Application Insights exporter (`APPLICATIONINSIGHTS_CONNECTION_STRING`, injected by the Foundry platform for hosted agents) | OTel spans `invoke_agent`, `chat`, `execute_tool`; `tool_audit` log lines | `AppDependencies` (GenAI spans, `AppRoleName` `agent-maf` / `agent-langgraph`), `AppGenAIContent`, `AppTraces`, `AppRequests` | ![GA](./assets/badges/ga.svg) prompt and hosted agents ([Learn](https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-agent-concept)) |

> [!NOTE]
> There is **no Foundry Agent Service-specific diagnostic category**. Agent-level observability comes from OpenTelemetry traces exported to Application Insights; Foundry export is GA for prompt and hosted agents and Preview for workflow and external agents. The OpenTelemetry GenAI semantic conventions (`chat {model}`, `create_agent`, `invoke_agent {agent}`, `execute_tool {tool}`) are still marked *Development* upstream, so treat attribute names as subject to change ([OpenTelemetry GenAI](https://opentelemetry.io/docs/specs/semconv/gen-ai/)).

APIM's built-in analytics also gains a *Language models* view for token and model usage. It is useful for a quick look, but classic APIM analytics retires in March 2027, so the saved queries and workbook here deliberately rely on Log Analytics instead ([APIM monitoring](https://learn.microsoft.com/en-us/azure/api-management/monitor-api-management)).

## LLM message logging and privacy

<img src="./assets/icons/api-management.svg" width="24" alt=""/> API Management can log the full prompt and completion text of every model call into `ApiManagementGatewayLlmLog` ([LLM logging](https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-llm-logs)). The demo turns it on by default so query 06 has something to show.

| Setting | Value in this demo | Notes |
|---|---|---|
| Switch | `ENABLE_LLM_MESSAGE_LOGGING` (default `true`) | Sets APIM `largeLanguageModel` logging to `logs: enabled` and `messages: all`; `false` sets `disabled` / `none`. |
| Chunking | 32 KB (32,768-byte) chunks with sequence numbers | Large messages are split across rows and re-assembled by `CorrelationId`. |
| Platform cap | 2 MB per message (hard limit) | Separate from generic request/response body logging, which is limited to 8,192 bytes. |
| Demo cap | `maxSizeInBytes: 262144` (256 KB) for requests and responses | Set in `gateway-apimv2.bicep`; lower it further for shared environments. |
| Generic body logging | Disabled (`bytes: 0`) | Tool and REST payloads are not logged by the gateway. |

> [!WARNING]
> **Prompts and completions are customer data.** They can contain personal data, business secrets or confidential identifiers. Enable `ENABLE_LLM_MESSAGE_LOGGING` only in demo or approved audit scopes, restrict workspace access with Azure RBAC (the workspace is configured for resource-permission access), set `LOG_RETENTION_DAYS` deliberately, and set `ENABLE_LLM_MESSAGE_LOGGING=false` for any environment that carries real data. The `tool_audit` record never contains tokens or full payloads by design.

## Token metrics and dimensions

Token accounting has two layers: the **log** (`ApiManagementGatewayLlmLog`, per request) and the **metric** emitted by the gateway policy. The Standard v2 gateway uses the `llm-*` policy family ([llm-emit-token-metric](https://learn.microsoft.com/en-us/azure/api-management/llm-emit-token-metric-policy), [llm-token-limit](https://learn.microsoft.com/en-us/azure/api-management/llm-token-limit-policy)).

| Signal | <img src="./assets/icons/api-management.svg" width="20" alt=""/> Where it is set | Dimensions / key | Used for |
|---|---|---|---|
| `llm-emit-token-metric` | Model API policy | Agent `appid`, user `oid`, API, subscription | Per-agent and per-user consumption in Azure Monitor metrics. The workbook uses logs/spans instead; it does not query this custom metric directly. |
| `llm-token-limit` | Model API policy | Counter key = validated `azp` claim; `TOKEN_LIMIT_TPM_PER_AGENT` (default 20,000 tokens per minute) | Per-agent throttling; a breach returns HTTP 429 and feeds the `token-limit-throttling-spike` alert. |
| `llm-content-safety` | Model API policy, gated by `ENABLE_CONTENT_SAFETY` | Content-safety backend | Blocks harmful prompts; surfaces in query 09 and the `content-safety-blocks` alert. |
| `ApiManagementGatewayLlmLog` | Diagnostic category `GatewayLlmLogs` | `CorrelationId`, `ModelName`, `PromptTokens`, `CompletionTokens`, `TotalTokens` | Per-request token audit; joined to the tool audit by `gateway_request_id`. |

> [!TIP]
> To attribute tokens to a person, join `ApiManagementGatewayLlmLog.CorrelationId` to the audit record's `gateway_request_id` (query 02 and query 01 do this for you). The `x-gw-user-oid` and `x-gw-agent-appid` headers added by APIM are the source of the dimensions.

Correlation must be present in the actual source rows. Model and tool requests can have different gateway request IDs; a missing join remains unknown token attribution, not zero spend. Query 02 keeps hosted-agent `agent_name` separate from an actual `agent_appid`. Gateway and agent token observations describe overlapping work and must not be added together.

## The audit record

Every tool backend (catalog MCP server and records API) writes **one JSON line** per call with `event: "tool_audit"`. It goes to `ContainerAppConsoleLogs_CL` and, where the agent exports telemetry, to `AppTraces`.

| Field | <img src="./assets/icons/code.svg" width="20" alt=""/> Meaning |
|---|---|
| `timestamp`, `service`, `tool`, `operation` | When, which backend, which tool, which operation. |
| `trace_id`, `span_id`, `traceparent` | W3C trace context forwarded unchanged by the gateway. |
| `decision`, `reason` | `allowed` or `denied`, plus the policy reason. |
| `human_principal` | `{ oid }` of the delegated user, or `null` for autonomous calls. |
| `agent_principal` | `{ appid, oid, actor_facets }` of the calling agent identity. |
| `gateway_request_id` | APIM `context.RequestId` - the join key to the gateway tables. |
| `gateway` | `apimv2` when any `x-gw-*` identity header is present, `aigateway` when `x-gw-caller` is present, `null` when called directly. |
| `caller` | `aigw-runtime-key:agents` on the AI Gateway tier path; `null` otherwise. |
| `domain_profile`, `latency_ms`, `status_code` | Workload profile and result. |

Identity travels in the headers `x-gw-agent-appid`, `x-gw-agent-oid`, `x-gw-user-oid`, `x-gw-actor-facets` and `x-gw-request-id`; `traceparent` is forwarded unchanged.

> [!NOTE]
> On the AI Gateway tier the runtime key proves *possession* of a gateway-scoped key, not a principal. Expect `gateway = "aigateway"`, `caller = "aigw-runtime-key:agents"` and `agent_principal = null` - an honest limitation, not a defect. See [doc 11](./11-demo-walkthrough.md) for how to present it.

## Correlation join keys

| Key | Left side | Right side | Why it matters |
|---|---|---|---|
| `traceparent` / `trace_id` | Agent spans and `tool_audit` lines | `AppRequests.OperationId`, `AppDependencies.OperationId` | Connects the agent turn to the backend span. |
| `gateway_request_id` | `tool_audit.gateway_request_id` | `CorrelationId` on `ApiManagementGatewayLogs`, `ApiManagementGatewayLlmLog`, `ApiManagementGatewayMCPLog` | Connects the tool decision to the gateway row and the token spend. |
| `SessionId` | `ApiManagementGatewayMCPLog.SessionId` | MCP client session | Groups the calls of one MCP session. |
| Agent `appid` / user `oid` | Audit record and metric dimensions | `AADServicePrincipalSignInLogs.AppId`, `AuditLogs` | Ties a call to an Entra sign-in event when Entra export is enabled. |

## The saved queries

The new [browser console S5](./11-demo-walkthrough.md#s5--run-bounded-saved-kql-and-inspect-actual-evidence) runs only the fixed saved-query allowlist **01-11**, using backend managed identity with **Log Analytics Reader** at workspace scope. It supplies a **one-hour API timespan** and appends **`take 200`**; query **04** accepts a trace ID. It displays rows, detailed responses and trace IDs, not a fabricated workbook or alert result. No arbitrary KQL is accepted. **“Passed” means the query returned rows, not that an audit assertion was validated.** Review row contents to establish the actual claim.

**Empty results are `not_run`**, with ingestion-delay/no-evidence guidance, never a pass. Response-header trace IDs are advisory correlation handles; actual source rows must establish propagation/tool use. The [2026-10-16 follow-up](./04-testing.md#live-follow-up-2026-10-16) records limited console/workbook checks and remaining browser acceptance work; historical saved-query evidence below comes from the earlier script-driven run.

Eleven queries are deployed to a Log Analytics **query pack** by `modules/querypack.bicep` (names `NN-slug`, loaded with `loadTextContent` from `infra/monitoring/queries/`). Open the workspace in the portal, choose *Queries*, and filter by the pack ([query packs](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/query-packs)). From a terminal, run any query with `python scripts/run_audit_queries.py --query 01` and `--trace-id <id>` for query 04.

The KQL blocks below are quoted verbatim from the files in `infra/monitoring/queries/`.

### <img src="./assets/icons/managed-identity.svg" width="28" alt=""/> 01 - Who called which tool

| | |
|---|---|
| **Saved query** | `01-who-called-which-tool` |
| **Purpose** | The headline audit question: human, agent, tool, decision, tokens and time in one row. |
| **Tables** | `ContainerAppConsoleLogs_CL`, `AppTraces`, `ApiManagementGatewayMCPLog`, `ApiManagementGatewayLlmLog` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: who (human + agent) called which tool/backend, with tokens, when, and was it allowed? Tables: ContainerAppConsoleLogs_CL, AppTraces, ApiManagementGatewayMCPLog, ApiManagementGatewayLlmLog.
let ToolAudit =
    union isfuzzy=true
        (ContainerAppConsoleLogs_CL | project TimeGenerated, RawLog=tostring(Log_s)),
        (AppTraces | project TimeGenerated, RawLog=tostring(Message))
    | extend audit = parse_json(RawLog)
    | where tostring(audit.event) == "tool_audit"
    | project
        TimeGenerated,
        trace_id = tostring(audit.trace_id),
        service = tostring(audit.service),
        tool = tostring(audit.tool),
        operation = tostring(audit.operation),
        decision = tostring(audit.decision),
        reason = tostring(audit.reason),
        human_oid = tostring(audit.human_principal.oid),
        agent_appid = tostring(audit.agent_principal.appid),
        agent_oid = tostring(audit.agent_principal.oid),
        gateway = tostring(audit.gateway),
        caller = tostring(audit.caller),
        gateway_request_id = tostring(audit.gateway_request_id),
        status_code = toint(audit.status_code);
let GatewayTools =
    ApiManagementGatewayMCPLog
    | project McpTime=TimeGenerated, CorrelationId, ServerName, ToolName, Method, TransportType, Error;
let Tokens =
    ApiManagementGatewayLlmLog
    | summarize PromptTokens=sum(PromptTokens), CompletionTokens=sum(CompletionTokens), TotalTokens=sum(TotalTokens) by CorrelationId;
ToolAudit
| join kind=leftouter GatewayTools on $left.gateway_request_id == $right.CorrelationId
| join kind=leftouter Tokens on CorrelationId
| project TimeGenerated, trace_id, gateway_request_id, gateway, caller, human_oid, agent_appid, agent_oid, service, tool=coalesce(tool, ToolName), operation=coalesce(operation, Method), decision, reason, status_code, PromptTokens, CompletionTokens, TotalTokens, ServerName, TransportType
| order by TimeGenerated desc
```

</details>

### <img src="./assets/icons/cost-management.svg" width="28" alt=""/> 02 - Token usage by agent and user

| | |
|---|---|
| **Saved query** | `02-token-usage-by-agent-and-user` |
| **Purpose** | Token consumption per gateway lane, agent and model. The APIM LLM log carries no agent identity, so per-agent figures come from the hosted-agent `gen_ai.*` spans; the AI Gateway tier rows come from `AppRequests` measurements. |
| **Tables** | `ApiManagementGatewayLlmLog`, `AppRequests`, `AppDependencies`, `AppTraces` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: how many LLM tokens were consumed by agent and delegated user? Tables: ApiManagementGatewayLlmLog (Standard v2 APIM), AppRequests (AI Gateway tier built-in App Insights telemetry, AppRoleName "aigw-*"), AppDependencies (hosted-agent GenAI spans), AppTraces.
// The gateway LLM log carries no agent identity, so per-agent attribution comes from the hosted-agent gen_ai spans (gen_ai.agent.name, gen_ai.usage.*); user_oid is only populated when a delegated user is present (see query 01).
let AgentContext =
    AppTraces
    | where Message has "agent_appid" or tostring(Properties.agent_appid) != ""
    | project CorrelationId=tostring(Properties.gateway_request_id), agent_appid=tostring(Properties.agent_appid), user_oid=tostring(Properties.user_oid)
    | where isnotempty(CorrelationId)
    | summarize agent_appid=take_any(agent_appid), user_oid=take_any(user_oid) by CorrelationId;
let ApimLlmLog =
    ApiManagementGatewayLlmLog
    | summarize PromptTokens=sum(PromptTokens), CompletionTokens=sum(CompletionTokens), Requests=count() by CorrelationId, ModelName
    | join kind=leftouter AgentContext on CorrelationId
    | summarize Requests=sum(Requests), PromptTokens=sum(PromptTokens), CompletionTokens=sum(CompletionTokens) by agent_appid, user_oid, ModelName
    | extend Source="apim-standard-v2-llm-log", agent_name="";
let TierRequests =
    AppRequests
    | where AppRoleName startswith "aigw-" and Name has "/models/"
    | extend m=todynamic(Measurements)
    | summarize Requests=count(), PromptTokens=tolong(sum(todouble(m["gen_ai.usage.input_tokens"]))), CompletionTokens=tolong(sum(todouble(m["gen_ai.usage.output_tokens"])))
    | extend Source="aigateway-tier-app-insights", agent_appid="", agent_name="", user_oid="", ModelName="";
let AgentSpans =
    AppDependencies
    | extend p=todynamic(Properties)
    | where tostring(p["gen_ai.operation.name"]) == "chat"
    | summarize Requests=count(), PromptTokens=sum(tolong(p["gen_ai.usage.input_tokens"])), CompletionTokens=sum(tolong(p["gen_ai.usage.output_tokens"])) by agent_name=coalesce(tostring(p["gen_ai.agent.name"]), AppRoleName), ModelName=tostring(p["gen_ai.request.model"])
    | extend Source="hosted-agent-genai-span", agent_appid="", user_oid="";
union isfuzzy=true ApimLlmLog, TierRequests, AgentSpans
| extend TotalTokens=PromptTokens + CompletionTokens
| project Source, agent_appid, agent_name, user_oid, ModelName, Requests, PromptTokens, CompletionTokens, TotalTokens
| order by TotalTokens desc
```

</details>

### <img src="./assets/icons/alerts.svg" width="28" alt=""/> 03 - Denied and throttled requests

| | |
|---|---|
| **Saved query** | `03-denied-and-throttled-requests` |
| **Purpose** | Every 401/403/429 at the gateway, every MCP denial and every `denied` audit decision in one list. |
| **Tables** | `ApiManagementGatewayLogs`, `ApiManagementGatewayMCPLog`, `ContainerAppConsoleLogs_CL`, `AppTraces` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: which gateway requests were denied or throttled? Tables: ApiManagementGatewayLogs, ApiManagementGatewayMCPLog, ContainerAppConsoleLogs_CL, AppTraces.
let AuditDenied =
    union isfuzzy=true
        (ContainerAppConsoleLogs_CL | project TimeGenerated, RawLog=tostring(Log_s)),
        (AppTraces | project TimeGenerated, RawLog=tostring(Message))
    | extend audit=parse_json(RawLog)
    | where tostring(audit.event) == "tool_audit"
    | where tostring(audit.decision) == "denied"
    | project TimeGenerated, Source="tool_audit", CorrelationId=tostring(audit.gateway_request_id), Status=toint(audit.status_code), Reason=tostring(audit.reason), Tool=tostring(audit.tool);
let GatewayDenied =
    ApiManagementGatewayLogs
    | extend ErrorText=tostring(column_ifexists("ErrorMessage", "")), BackendMessage=tostring(column_ifexists("BackendResponseMessage", ""))
    | where ResponseCode in (401, 403, 429) or BackendResponseCode in (401, 403, 429)
    | project TimeGenerated, Source="apim", CorrelationId, Status=coalesce(ResponseCode, BackendResponseCode), Reason=coalesce(ErrorText, BackendMessage), Tool="";
let McpDenied =
    ApiManagementGatewayMCPLog
    | where Error has_any ("Forbidden", "throttl", "Unauthorized") or ErrorType has_any ("Forbidden", "Throttled", "Unauthorized")
    | project TimeGenerated, Source="mcp", CorrelationId, Status=int(null), Reason=Error, Tool=ToolName;
union AuditDenied, GatewayDenied, McpDenied
| order by TimeGenerated desc
```

</details>

### <img src="./assets/icons/application-insights.svg" width="28" alt=""/> 04 - End-to-end trace

| | |
|---|---|
| **Saved query** | `04-end-to-end-trace` (parameter `traceId`) |
| **Purpose** | Every known hop for a W3C trace id or an APIM correlation id, ordered by time. Powers the workbook trace lookup. |
| **Tables** | `AppRequests`, `AppDependencies`, `AppTraces`, `AppGenAIContent`, `ContainerAppConsoleLogs_CL`, `ApiManagementGatewayLogs`, `ApiManagementGatewayMCPLog`, `ApiManagementGatewayLlmLog` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: show evidenced hops for a trace or APIM correlation id. Gateway rows link through tool_audit.gateway_request_id, not the API operation name.
declare query_parameters(traceId:string = "");
let ToolAudit =
    union isfuzzy=true
        (datatable(TimeGenerated:datetime, RawLog:string)[]),
        (ContainerAppConsoleLogs_CL | project TimeGenerated, RawLog=tostring(Log_s)),
        (AppTraces | project TimeGenerated, RawLog=tostring(Message))
    | extend audit=parse_json(RawLog)
    | where tostring(audit.event) == "tool_audit"
    | project TimeGenerated, Source="tool_audit", Name=tostring(audit.tool), OperationId=tostring(audit.trace_id),
        ParentId=tostring(audit.span_id), CorrelationId=tostring(audit.gateway_request_id),
        Message=strcat(audit.decision, " ", audit.status_code), DurationMs=todouble(audit.latency_ms), Properties=audit;
let GatewayIds = ToolAudit
    | where isnotempty(traceId) and (OperationId == traceId or CorrelationId == traceId)
    | where isnotempty(CorrelationId)
    | distinct CorrelationId;
union isfuzzy=true
    ToolAudit,
    (AppRequests | project TimeGenerated, Source="AppRequests", Name, OperationId, ParentId, CorrelationId="", Message=tostring(Success), DurationMs=DurationMs, Properties),
    (AppDependencies | project TimeGenerated, Source="AppDependencies", Name, OperationId, ParentId, CorrelationId="", Message=tostring(Success), DurationMs=DurationMs, Properties),
    (AppTraces | project TimeGenerated, Source="AppTraces", Name=tostring(Properties["span.name"]), OperationId, ParentId, CorrelationId=tostring(Properties.gateway_request_id), Message, DurationMs=real(null), Properties),
    (ApiManagementGatewayLogs | project TimeGenerated, Source="ApiManagementGatewayLogs", Name=ApiId, OperationId="", ParentId="", CorrelationId, Message=strcat(ResponseCode, " ", LastErrorMessage), DurationMs=todouble(TotalTime), Properties=bag_pack("ApiId", ApiId, "LastErrorReason", LastErrorReason)),
    (ApiManagementGatewayMCPLog | project TimeGenerated, Source="ApiManagementGatewayMCPLog", Name=ToolName, OperationId="", ParentId="", CorrelationId, Message=Error, DurationMs=real(null), Properties=bag_pack("ServerName", ServerName, "Method", Method, "SessionId", SessionId)),
    (ApiManagementGatewayLlmLog | project TimeGenerated, Source="ApiManagementGatewayLlmLog", Name=ModelName, OperationId="", ParentId="", CorrelationId, Message=strcat("tokens=", TotalTokens), DurationMs=real(null), Properties=bag_pack("PromptTokens", PromptTokens, "CompletionTokens", CompletionTokens)),
    (AppGenAIContent | project TimeGenerated, Source="AppGenAIContent", Name=AgentName, OperationId=TraceId, ParentId=ParentSpanId, CorrelationId="", Message=strcat("model=", ModelName), DurationMs=real(null), Properties=bag_pack("SpanId", SpanId, "AgentId", AgentId))
| where isempty(traceId) or OperationId == traceId or ParentId == traceId or CorrelationId == traceId or tostring(Properties.trace_id) == traceId or CorrelationId in (GatewayIds)
| order by TimeGenerated asc
```

</details>

### <img src="./assets/icons/api-management.svg" width="28" alt=""/> 05 - MCP tool calls

| | |
|---|---|
| **Saved query** | `05-mcp-tool-calls` |
| **Purpose** | Which MCP servers and tools were invoked through APIM, over which transport, by which client, with which error. |
| **Tables** | `ApiManagementGatewayMCPLog` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: what MCP tools were called through APIM? Tables: ApiManagementGatewayMCPLog.
ApiManagementGatewayMCPLog
| project TimeGenerated, CorrelationId, ServerName, McpServerEndpoint, ToolName, Method, TransportType, SessionId, ClientName, ClientVersion, Error, ErrorType
| order by TimeGenerated desc
```

</details>

### <img src="./assets/icons/azure-openai.svg" width="28" alt=""/> 06 - LLM prompts and completions

| | |
|---|---|
| **Saved query** | `06-llm-prompts-and-completions` |
| **Purpose** | The 100 most recent LLM message logs with token accounting. Sensitive - see the [privacy warning](#llm-message-logging-and-privacy). |
| **Tables** | `ApiManagementGatewayLlmLog` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: sample LLM message logs and token accounting. Tables: ApiManagementGatewayLlmLog.
ApiManagementGatewayLlmLog
| extend
    ModelName = tostring(column_ifexists("ModelName", column_ifexists("Model", ""))),
    PromptTokens = toint(column_ifexists("PromptTokens", int(null))),
    CompletionTokens = toint(column_ifexists("CompletionTokens", int(null))),
    TotalTokens = toint(column_ifexists("TotalTokens", int(null))),
    PromptMessages = tostring(column_ifexists("PromptMessages", column_ifexists("RequestMessages", ""))),
    CompletionMessages = tostring(column_ifexists("CompletionMessages", column_ifexists("ResponseMessages", "")))
| project TimeGenerated, CorrelationId, ModelName, PromptTokens, CompletionTokens, TotalTokens, PromptMessages, CompletionMessages
| order by TimeGenerated desc
| take 100
```

</details>

### <img src="./assets/icons/entra-id.svg" width="28" alt=""/> 07 - Agent identity sign-ins

| | |
|---|---|
| **Saved query** | `07-agent-identity-sign-ins` |
| **Purpose** | Service principal and managed identity sign-ins, plus audit events that mention an agent. Returns rows only after Entra export is enabled (`ENABLE_ENTRA_DIAGNOSTICS`). |
| **Tables** | `AADServicePrincipalSignInLogs`, `AADManagedIdentitySignInLogs`, `AuditLogs` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: which agent-related service principal or managed identity sign-ins succeeded/failed? Tables: AADServicePrincipalSignInLogs, AADManagedIdentitySignInLogs, AuditLogs.
union isfuzzy=true
    (datatable(TimeGenerated:datetime, Source:string, ServicePrincipalId:string, ServicePrincipalName:string, AppId:string, ResourceDisplayName:string, ResultType:string, ResultDescription:string, IPAddress:string, ConditionalAccessStatus:string)[]),
    (AADServicePrincipalSignInLogs | project TimeGenerated, Source="ServicePrincipal", ServicePrincipalId, ServicePrincipalName, AppId, ResourceDisplayName, ResultType, ResultDescription, IPAddress, ConditionalAccessStatus),
    (AADManagedIdentitySignInLogs | project TimeGenerated, Source="ManagedIdentity", ServicePrincipalId, ServicePrincipalName, AppId, ResourceDisplayName, ResultType, ResultDescription, IPAddress, ConditionalAccessStatus),
    (AuditLogs | where tostring(TargetResources) has "agent" or OperationName has "agent" | project TimeGenerated, Source="Audit", ServicePrincipalId="", ServicePrincipalName=OperationName, AppId="", ResourceDisplayName=tostring(TargetResources), ResultType=tostring(Result), ResultDescription=tostring(ResultReason), IPAddress="", ConditionalAccessStatus="")
| order by TimeGenerated desc
```

</details>

### <img src="./assets/icons/activity-log.svg" width="28" alt=""/> 08 - Control-plane changes

| | |
|---|---|
| **Saved query** | `08-control-plane-changes` |
| **Purpose** | Who changed the gateway, Foundry, Key Vault, Container Apps or monitoring resources. Requires `ENABLE_ACTIVITY_LOG_EXPORT`. |
| **Tables** | `AzureActivity` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: who changed gateway, Foundry, Key Vault, Container Apps, or monitoring resources? Tables: AzureActivity.
union isfuzzy=true
    (datatable(TimeGenerated:datetime, Caller:string, OperationNameValue:string, ActivityStatusValue:string, ResourceGroup:string, ResourceProviderValue:string, ResourceId:string, CorrelationId:string, Properties:string)[]),
    AzureActivity
| where ResourceProviderValue in~ ("MICROSOFT.APIMANAGEMENT", "MICROSOFT.COGNITIVESERVICES", "MICROSOFT.APP", "MICROSOFT.KEYVAULT", "MICROSOFT.INSIGHTS", "MICROSOFT.OPERATIONALINSIGHTS")
| project TimeGenerated, Caller, OperationNameValue, ActivityStatusValue, ResourceGroup, ResourceProviderValue, ResourceId, CorrelationId, Properties
| order by TimeGenerated desc
```

</details>

### <img src="./assets/icons/content-safety.svg" width="28" alt=""/> 09 - Content-safety blocks

| | |
|---|---|
| **Saved query** | `09-content-safety-blocks` |
| **Purpose** | Requests blocked by gateway or model content-safety controls. |
| **Tables** | `ApiManagementGatewayLogs` (`LastErrorMessage`), `ApiManagementGatewayLlmLog`, `AppTraces` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: which requests were blocked by gateway or model content-safety controls? Tables: ApiManagementGatewayLogs, ApiManagementGatewayLlmLog, AppTraces.
union isfuzzy=true
    (ApiManagementGatewayLogs | where LastErrorMessage has_any ("content safety", "content_filter", "jailbreak", "blocked") | project TimeGenerated, Source="APIM", CorrelationId, Detail=LastErrorMessage, ApiId, ResponseCode),
    (ApiManagementGatewayLlmLog | extend Prompt = tostring(column_ifexists("PromptMessages", column_ifexists("RequestMessages", ""))), Completion = tostring(column_ifexists("CompletionMessages", column_ifexists("ResponseMessages", ""))) | where Prompt has_any ("content_filter", "blocked") or Completion has_any ("content_filter", "blocked") | project TimeGenerated, Source="LLM", CorrelationId, Detail=strcat("tokens=", tostring(column_ifexists("TotalTokens", int(null)))), ApiId="", ResponseCode=int(null)),
    (AppTraces | where Message has_any ("content safety", "content_filter", "blocked") | project TimeGenerated, Source="AppTraces", CorrelationId=tostring(Properties.gateway_request_id), Detail=Message, ApiId="", ResponseCode=int(null))
| order by TimeGenerated desc
```

</details>

### <img src="./assets/icons/foundry.svg" width="28" alt=""/> 10 - Foundry audit

| | |
|---|---|
| **Saved query** | `10-foundry-audit` |
| **Purpose** | Foundry account and project audit and trace events, plus agent spans in Application Insights. |
| **Tables** | `AzureDiagnostics`, `AppTraces` |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: what Foundry account/project audit and trace events occurred? Tables: AzureDiagnostics, AppTraces.
union isfuzzy=true
    (AzureDiagnostics | where ResourceProvider == "MICROSOFT.COGNITIVESERVICES" | project TimeGenerated, Source="AzureDiagnostics", Category, OperationName, ResultType, CorrelationId, ResourceId, Detail=properties_s),
    (AppTraces | where tostring(Properties["service.name"]) has_any ("foundry", "agent") or Message has_any ("invoke_agent", "execute_tool", "chat") | project TimeGenerated, Source="AppTraces", Category=tostring(Properties.Category), OperationName=tostring(Properties["span.name"]), ResultType=tostring(Properties.Success), CorrelationId=tostring(Properties.gateway_request_id), ResourceId=tostring(Properties.ResourceId), Detail=Message)
| order by TimeGenerated desc
```

</details>

### <img src="./assets/icons/ai-gateway.svg" width="28" alt=""/> 11 - AI Gateway tier telemetry

| | |
|---|---|
| **Saved query** | `11-ai-gateway-tier-telemetry` |
| **Purpose** | Compares AI Gateway tier telemetry (LLM and MCP calls in `AppRequests`, plus the MCP log) with Standard v2 LLM logs and the hosted-agent GenAI spans, per hour and route. |
| **Tables** | `AppRequests`, `ApiManagementGatewayMCPLog`, `ApiManagementGatewayLlmLog`, `AppDependencies` |
| **Status** | ![Live tested](./assets/badges/live-tested.svg) Rewritten over real tables after the v1.2 live run (30 rows). |

<details><summary><b>Show KQL</b></summary>

```kusto
// Question: how does AI Gateway tier telemetry compare with Standard v2 APIM LLM logs and the hosted-agent GenAI spans? Tables: AppRequests (AI Gateway tier built-in App Insights telemetry, AppRoleName "aigw-*"; tokens in Measurements gen_ai.usage.*), ApiManagementGatewayMCPLog (AI Gateway tier MCP log), ApiManagementGatewayLlmLog (Standard v2), AppDependencies (hosted-agent gen_ai.* spans).
// Verified live: the AI Gateway tier writes no ApiManagementGatewayLlmLog rows; its LLM telemetry is the AppRequests row per call.
let Tier =
    AppRequests
    | where AppRoleName startswith "aigw-"
    | extend m=todynamic(Measurements)
    | extend Surface=case(Name has "/models/", "llm", Name has "/toolservers/", "mcp", "other")
    | summarize Requests=count(), Failed=countif(Success == false), InputTokens=tolong(sum(todouble(m["gen_ai.usage.input_tokens"]))), OutputTokens=tolong(sum(todouble(m["gen_ai.usage.output_tokens"]))), AvgDurationMs=avg(DurationMs) by Gateway="aigateway-tier", Surface, Route=Name, TimeGenerated=bin(TimeGenerated, 1h);
let TierMcp =
    ApiManagementGatewayMCPLog
    | summarize Requests=count(), Failed=countif(isnotempty(Error)), InputTokens=long(null), OutputTokens=long(null), AvgDurationMs=real(null) by Gateway="mcp-resource-log", ResourceId=tostring(_ResourceId), Surface="mcp", Route=strcat(McpServerEndpoint, " ", Method), TimeGenerated=bin(TimeGenerated, 1h);
let StandardV2 =
    ApiManagementGatewayLlmLog
    | summarize Requests=count(), Failed=long(0), InputTokens=sum(tolong(PromptTokens)), OutputTokens=sum(tolong(CompletionTokens)), AvgDurationMs=real(null) by Gateway="apim-standard-v2", Surface="llm", Route=strcat("model=", ModelName), TimeGenerated=bin(TimeGenerated, 1h);
let AgentSpans =
    AppDependencies
    | extend p=todynamic(Properties)
    | where isnotempty(tostring(p["gen_ai.operation.name"]))
    | summarize Requests=count(), Failed=countif(Success == false), InputTokens=sum(tolong(p["gen_ai.usage.input_tokens"])), OutputTokens=sum(tolong(p["gen_ai.usage.output_tokens"])), AvgDurationMs=avg(DurationMs) by Gateway=strcat("hosted-agent:", AppRoleName), Surface=tostring(p["gen_ai.operation.name"]), Route=tostring(p["gen_ai.request.model"]), TimeGenerated=bin(TimeGenerated, 1h);
union isfuzzy=true Tier, TierMcp, StandardV2, AgentSpans
| project TimeGenerated, Gateway, Surface, Route, ResourceId, Requests, Failed, InputTokens, OutputTokens, AvgDurationMs
| order by TimeGenerated desc, Gateway asc, Surface asc
```

</details>

## AI Gateway tier telemetry (preview)

![Public preview](./assets/badges/public-preview.svg) ![Live tested](./assets/badges/live-tested.svg) <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> The AI Gateway tier is observed through the Application Insights resource connected to it, not through APIM diagnostic categories. The v1.2 live run showed that it does **not** write `ApiManagementGatewayLlmLog`.

| What you want | Where it lands |
|---|---|
| LLM call (model, duration, success) | `AppRequests`, `AppRoleName` `aigw-<name> <region>`, `Name` `POST /default/models/openai/v1/...` |
| Tokens | `AppRequests.Measurements["gen_ai.usage.input_tokens"]` and `["gen_ai.usage.output_tokens"]` |
| MCP tool call | `AppRequests` (`/default/toolservers/<name>/mcp`) and `ApiManagementGatewayMCPLog` (`ServerName`, `ToolName`, `Method`, `Error`) |
| Content-safety and forward-request hops | `AppDependencies` |

> [!CAUTION]
> No diagnostic setting is deployed for the tier because no tier-specific resource-log category was confirmed. Do not claim the tier provides Entra-validated caller identity: it authenticates with a gateway-scoped runtime `api-key`, so `agent_principal` is empty by design.

Payload logging is off by default. Never read `context.Response.Body` in an MCP policy - it buffers the response and breaks streaming ([MCP in API Management](https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview)).

## Workbook

<img src="./assets/icons/workbooks.svg" width="28" alt=""/> The workbook has **17 query panels**, including **two side-by-side token timecharts** with explicit input/output series and legends. Open it from the `WORKBOOK_ID` output ([workbooks](https://learn.microsoft.com/en-us/azure/azure-monitor/visualize/workbooks-overview)). The top time-range control (default **24 hours**) applies to every section.

| Section | Contents and filter scope |
|---|---|
| **Overview - token usage** | Gateway input/output tokens by lane and hosted-agent chat tokens in separate charts. Time range only; do not add the overlapping layers together. |
| **Token usage details** | Source/identity/model totals and gateway/agent observation tables. Time range only. |
| **Gateway health and tool activity** | Latency/5xx, audit identity/decision, MCP tools and sessions. Time range only. |
| **Security and platform audit** | Denials, content-safety signals, identity export, resource changes, Foundry, Key Vault and registry audit. Time range only. |
| **Trace investigation** | The optional trace input lives here and filters only the timeline and hosted-agent content. Blank shows recent hops. The timeline accepts W3C trace IDs or APIM correlation IDs; hosted-agent content matches W3C trace IDs only. |
| **APIM message sample** | Sensitive prompt/completion sample for the selected time range, not the trace input. Copy a sample's correlation ID into Trace investigation to inspect that request. |
| **Telemetry coverage** | Sources with ingested evidence in the selected time range. |

`infra/monitoring/workbook.json` is the layout, not a standalone import: `modules/workbook.bicep` binds the 11 saved KQL files into their panels at deployment, supplies the workspace scope, and substitutes the escaped trace input for query 04's SDK parameter declaration. Every panel also receives source-level `TimeGenerated {TimeRange:query}` filters, before joins, aggregation, time bins and row limits; filtering a finished totals table or binned timestamp would be too late. This includes inline audit/content/coverage queries. The Overview displays the selected label, start/end and bucket size. The saved KQL remains usable unchanged by the query pack and console, whose callers supply their own time range.

The two overview charts derive series from query 11, filtering gateway LLM and hosted-agent **chat** observations separately; parent `invoke_agent` spans and MCP rows are not added to the agent chart. For the charts only, the hourly source bins become `bin_at` buckets using `{TimeRange:grain}`, anchored at `{TimeRange:start}`. In KQL, Workbook start/end parameters already expand to datetime expressions: use `from {TimeRange:start} to {TimeRange:end}` directly, **not** `datetime({TimeRange:start})`, which produces an invalid nested expression. A single `Tokens` measure is segmented by a `Series` label such as `apim-standard-v2 / input` or `agent-maf / output`, rather than combining two Y measures with grouping.

`make-series` fills empty buckets across the selected start/end for each observed series, preventing the time axis from shrinking to the few timestamps that had traffic ([Workbook time-series guidance](https://learn.microsoft.com/en-us/azure/azure-monitor/visualize/workbooks-chart-visualizations#summarize-vs-make-series)). Zero-filled gaps are not new observations or proof of a passing control. If the selected window has no token observations, no synthetic gateway/agent series is created and the no-data message is shown. Each chart limits the intermediate result to **200 series**, then expands the timestamp/token arrays together with `mv-expand` into scalar **datetime `TimeGenerated`**, **long `Tokens`**, and **string `Series`** columns. Do not bind the dynamic arrays directly to chart axes: they can render as JSON category labels with zero numeric totals. The detail-table 200-row limit is not applied to the expanded chart points; for example, four series across seven days at three-hour intervals require all **224 points**. Saved-query detail panels return at most **200 rows**, hosted content **50**, and platform audit **100**, within the selected range. The workbook, query pack and console share maintained KQL rather than hand-copied versions. Updating the layout/KQL requires a workbook deployment; changing console application code alone does not update the workbook.

| Tile | Title | Answers | Backed by |
|---|---|---|---|
| `gateway-token-trend` | Gateway LLM tokens - APIM vs AI Gateway tier | How do input/output tokens compare by gateway lane over the selected window? | Query 11 filtered to gateway LLM observations; timechart |
| `agent-token-trend` | Hosted-agent chat tokens | Which agent chat spans recorded tokens over time? | Query 11 filtered to hosted-agent `chat` spans; separate timechart |
| `telemetry-coverage` | Sources with rows in the selected range | Which sources actually have ingested evidence? | Source table counts and latest timestamps |
| `who-called-which-tool` | Audit identity, tool and decision | What identity/caller was actually recorded? | Query 01 |
| `token-usage` | Token usage by source and recorded identity/model | Which layer recorded token consumption? | Query 02; names and application IDs are distinct |
| `standard-v2-vs-aigw-tier` | Gateway and hosted-agent observations | What did each telemetry layer record? | Query 11; MCP rows include `ResourceId`, not an assumed tier label |
| `tool-calls` | MCP methods, tools and sessions | Which MCP requests and tools were recorded? | Query 05 |
| `denied-throttled` | Denied and throttled | Where are controls firing? | Query 03 |
| `latency-5xx` | Gateway latency and 5xx (P95 + failures) | What latency and failures were observed? | APIM `TotalTime` and tier `AppRequests.DurationMs`, both milliseconds |
| `llm-sample` | LLM log sample | What do prompts and completions look like? | Query 06 |
| `hosted-agent-content` | Agent prompts/completions and tool content | What content was exported for an agent trace? | `AppGenAIContent`; sensitive content |
| `trace-lookup` | Trace/correlation timeline | Which hops can actually be linked? | Query 04 plus `tool_audit.gateway_request_id`; blank input is valid |
| `identity-sign-ins` | Entra sign-ins and agent audit | Which identity events were exported? | Query 07; requires Entra diagnostics |
| `control-plane-changes` | Resource changes | Which management operations were exported? | Query 08; requires Activity Log export |
| `content-safety` | Content-safety signals | Are there recorded filtering/block signals? | Query 09; inspect messages before attributing a policy |
| `foundry-audit` | Foundry audit and application traces | What account/project or application events were recorded? | Query 10 |
| `platform-audit` | Key Vault and registry audit | What vault/registry operations and results were logged? | `AzureDiagnostics`, `ContainerRegistryLoginEvents`, `ContainerRegistryRepositoryEvents` |

Empty panels mean **no evidence in the selected range**, not a passing control. Optional identity/Activity Log queries have typed empty inputs to retain a result schema when sources are absent; Azure can still report source-resolution warnings for tables that do not exist. Do not treat partial results as complete evidence. Coverage lists sources with rows, not proof that every diagnostic switch is enabled. Missing cross-system links remain missing: APIM's `OperationId` is an API operation name, not a W3C trace ID. The timeline uses `TotalTime`/`LastErrorMessage` for gateway rows and can link them through an actual tool audit record.

LLM and hosted-agent message panels expose sensitive content already present in the workspace; they do not enable additional logging. The workbook does not deploy Sentinel/Defender, surface custom metric dimensions, or prove alert firing. Use the Azure Monitor metrics and Alerts views for those documented surfaces.

## Alerts

<img src="./assets/icons/alerts.svg" width="28" alt=""/> `modules/alerts.bicep` creates scheduled-query rules ([log search alerts](https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/alerts-types#log-alerts)) when `ENABLE_ALERTS=true`. All rules use **severity 2**, evaluate every 5 minutes (`PT5M`) over a 15-minute window (`PT15M`). An action group `ag-hosted-agent-gateway` is created only when `ALERT_EMAIL` is set; without it the rules still fire and are visible in the portal.

| Alert | Icon | Condition | Threshold | Severity |
|---|---|---|---|---|
| `token-limit-throttling-spike` | <img src="./assets/icons/api-management.svg" width="20" alt=""/> | HTTP 429 on an API whose id contains `llm` | 5 or more | 2 |
| `denied-tool-calls` | <img src="./assets/icons/managed-identity.svg" width="20" alt=""/> | MCP error `Forbidden`, or HTTP 401/403 | 1 or more | 2 |
| `gateway-5xx-rate` | <img src="./assets/icons/monitor.svg" width="20" alt=""/> | HTTP 5xx at the gateway | 3 or more | 2 |
| `content-safety-blocks` | <img src="./assets/icons/content-safety.svg" width="20" alt=""/> | Error message mentions `content`, or backend 403 | 1 or more | 2 |
| `agent-sign-in-failures` | <img src="./assets/icons/entra-id.svg" width="20" alt=""/> | `ResultType != 0` on service principal or managed identity sign-ins. Created only when `ENABLE_ENTRA_DIAGNOSTICS=true` | 1 or more | 2 |

## Optional: Microsoft Sentinel and Defender for Cloud

![Opt-in](./assets/badges/opt-in.svg) The demo prepares the workspace for a SIEM and recommends - but does not deploy - Defender plans.

| Product | What it adds | Status | In this demo |
|---|---|---|---|
| <img src="./assets/icons/sentinel.svg" width="20" alt=""/> **Microsoft Sentinel** ([overview](https://learn.microsoft.com/en-us/azure/sentinel/overview)) | SIEM / SOAR on the same workspace | ![GA](./assets/badges/ga.svg) | `ENABLE_SENTINEL=true` onboards the workspace (`modules/sentinel.bicep`). |
| <img src="./assets/icons/sentinel.svg" width="20" alt=""/> **Sentinel "OpenAI" solution** ([source](https://github.com/Azure/Azure-Sentinel/tree/master/Solutions/OpenAI)) | Content for Azure OpenAI audit data | Content-hub solution | Install manually; not deployed. |
| <img src="./assets/icons/sentinel.svg" width="20" alt=""/> **Sentinel "Agent 365" connector** | Agent activity from Microsoft Agent 365 | GA / Preview status not stated in sources checked | Install manually; not deployed. |
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> **APIM connector** | - | There is **no official Sentinel connector for API Management**; only a third-party ISV solution exists. | Query the workspace tables directly instead. |
| <img src="./assets/icons/defender-for-cloud.svg" width="20" alt=""/> **Defender for APIs** ([intro](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-apis-introduction)) | API threat detection and posture | ![GA](./assets/badges/ga.svg) (since 2023) | Recommended subscription plan. |
| <img src="./assets/icons/defender-for-cloud.svg" width="20" alt=""/> **Defender for AI Services** ([AI threat protection](https://learn.microsoft.com/en-us/azure/defender-for-cloud/ai-threat-protection)) | Runtime threat protection for Foundry / Azure OpenAI | ![GA](./assets/badges/ga.svg) | Recommended subscription plan. |
| <img src="./assets/icons/defender-for-cloud.svg" width="20" alt=""/> **Threat protection for AI agents** | Agent-level threat detection | ![Preview](./assets/badges/preview.svg) | Recommended; evaluate before relying on it. |

> [!NOTE]
> Defender plans are **subscription-level** choices with their own cost. The demo does not enable them, so the demo can run in a subscription where you do not own security policy.

## Retention and cost

<img src="./assets/icons/cost-management.svg" width="28" alt=""/> Monitoring cost is dominated by ingestion volume ([Azure Monitor pricing](https://azure.microsoft.com/pricing/details/monitor/)). The demo makes the main drivers explicit switches.

| Driver | Control | Default | Cost / risk note |
|---|---|---|---|
| Workspace retention | `LOG_RETENTION_DAYS` | `90` | Longer retention increases storage cost; raise it only to meet an audit requirement. |
| LLM prompt and completion text | `ENABLE_LLM_MESSAGE_LOGGING` | `true` | Largest single ingestion driver and a privacy risk; disable for real workloads. |
| GenAI telemetry from agents and tier | Application Insights sampling | Not configured | Spans per tool call add up under load; sample in production. |
| Activity Log export | `ENABLE_ACTIVITY_LOG_EXPORT` | `false` | Five categories at subscription scope; low volume, high audit value. |
| Entra diagnostics | `ENABLE_ENTRA_DIAGNOSTICS` | `false` | Tenant-wide sign-in logs can be high volume. |
| Sentinel | `ENABLE_SENTINEL` | `false` | Adds per-GB Sentinel analytics cost on top of ingestion. |
| Alerts | `ENABLE_ALERTS`, `ALERT_EMAIL` | `true`, blank | Scheduled-query rules are billed per evaluation. |

## Worked example: "who called which tool?"

Scenario: a field operator asks the agent to create a work order after checking part availability. Query 01 returns one row per tool call. The values below are **illustrative** (identifiers shortened).

| Time (UTC) | Human `oid` | Agent `appid` | Gateway | Tool | Decision | Tokens | Trace |
|---|---|---|---|---|---|---|---|
| 14:02:11 | `1111...` | `aaaa...` | `apimv2` | `check_availability` | allowed | 412 | `4bf9...` |
| 14:02:19 | `1111...` | `aaaa...` | `apimv2` | `create_record` | allowed | 655 | `4bf9...` |
| 14:03:40 | `1111...` | `aaaa...` | `apimv2` | `delete_record` | **denied** (not on the allow-list) | 0 | `71c2...` |

<table>
<tr>
<td width="56"><img src="./assets/icons/managed-identity.svg" width="40" alt=""/></td>
<td><b>How to read it.</b> The <i>human</i> column comes from the delegated user (<code>x-gw-user-oid</code>), the <i>agent</i> column from the agent identity (<code>x-gw-agent-appid</code>). The <code>trace</code> value is the key you paste into query 04 (or the workbook trace tile) to see the model call, the MCP call, the backend span and the gateway row on one timeline.</td>
</tr>
</table>

1. Run `python scripts/run_audit_queries.py --ids demo-ids.local.json --query 01` and pick a row.
2. Copy its `trace_id`, then run `python scripts/run_audit_queries.py --ids demo-ids.local.json --query 04 --trace-id <trace_id>`.
3. Confirm the denied call also appears in query 03 and, with alerts enabled, as a `denied-tool-calls` alert.

> [!TIP]
> If query 01 shows `agent_principal` empty with `caller = aigw-runtime-key:agents`, the call went through the AI Gateway tier - the expected, documented limitation. Switch to query 11 (or 02) for token and model telemetry on that lane.

## Live evidence

![live-tested](./assets/badges/live-tested.svg) for **both gateway lanes** (APIM Standard v2 and the AI Gateway tier) and **both agents** (MAF and LangGraph), run `fhagl1002` on 2026-10-02 in `eastus2`. See [04 - Testing](./04-testing.md#live-validation-2026-10-02).

After the live walkthrough, all eleven saved queries were run against the demo workspace with `python scripts/run_audit_queries.py`. Row counts per query:

[![Rows returned per saved audit query](./assets/evidence/audit-query-results.png)](./assets/evidence/audit-query-results.png)

*Source: live run 2026-10-02, eastus2.*

### What each query actually showed

| Query | Rows | Result | Finding |
|---|---|---|---|
| 01 Who called which tool | 75 | ![ok](./assets/badges/live-tested.svg) | Allowed MCP calls joined by trace id across both gateways |
| 02 Token usage | 5 | fixed | Rewritten as a union of the APIM LLM log, the tier's `AppRequests` measurements and the hosted-agent `chat` spans, so agent names are populated |
| 03 Denied and throttled | 70 | ![ok](./assets/badges/live-tested.svg) | The 429 probe against the AI Gateway tier (183 of 240 throttled) plus APIM 401s |
| 04 End-to-end trace | 104 | fixed | Pass `--trace-id`; the runner now substitutes the parameter. Gateway log rows do **not** join because `ApiManagementGatewayLogs` carries no trace id |
| 05 MCP tool calls | 67 | ![ok](./assets/badges/live-tested.svg) | `ApiManagementGatewayMCPLog` rows for `catalog_list_items` and `records_list_records` |
| 06 Prompts and completions | 100 | ![ok](./assets/badges/live-tested.svg) | Works with `column_ifexists` fallbacks for schema drift |
| 07 Entra sign-ins | 0 | environment | Needs `ENABLE_ENTRA_DIAGNOSTICS`; off in this run |
| 08 Activity log | 0 | environment | `AzureActivity` was not connected to the workspace |
| 09 Content safety | 0 | fixed | `ErrorMessage` does not exist; now uses `LastErrorMessage`. No content-safety blocks occurred |
| 10 Foundry control plane | 942 | ![ok](./assets/badges/live-tested.svg) | Foundry audit and request rows |
| 11 Gateway-tier telemetry | 30 | fixed | Rewritten over `AppRequests`, `ApiManagementGatewayMCPLog`, the LLM log and agent spans |

> [!NOTE]
> Empty results for 07, 08 and 09 reflect the environment (diagnostics off, no blocked content), not defects.

### What the AI Gateway tier recorded

Across the run the tier handled 255 LLM requests (4,489 input and 860 output tokens, 186 failed, almost all from the deliberate 429 probe), 34 catalog MCP calls and 26 records MCP calls.

| Fact | Detail |
|---|---|
| Role name | `aigw-<name> East US 2` in `AppRoleName` |
| LLM route | `POST /default/models/openai/v1/responses` |
| MCP routes | `/default/toolservers/catalog-mcp/mcp`, `/default/toolservers/records/mcp` |
| `ApiManagementGatewayLlmLog` | **No rows from the tier**; every row there is Standard v2 |

> [!CAUTION]
> In this run `agent_oid` and the human principal can be equal on the APIM v2 lane because the validation scripts call the gateway with the operator's own CLI token. That is a harness caveat; hosted agents calling as their instance identity separate the two columns.

### Observed workspace tables and columns

- `ApiManagementGatewayLogs`: `ApiId`, `OperationId`, `Url`, `ResponseCode`, `BackendResponseCode`, `BackendUrl`, `LastErrorMessage`, `LastErrorReason`, `TraceRecords`, `TotalTime`, `CallerIpAddress`. There is no `Properties` or `ErrorMessage` column.
- `ApiManagementGatewayMCPLog`: `CorrelationId`, `ApiType`, `TransportType`, `AuthenticationMethod`, `ServerName`, `McpServerEndpoint`, `ToolName`, `Method`, `ToolCount`, `SessionId`, `Error`, `ErrorType`.
- `ApiManagementGatewayLlmLog`: token columns plus message columns that drift by schema version (`ModelName`/`Model`, `PromptMessages`/`RequestMessages`, `CompletionMessages`/`ResponseMessages`). Queries must tolerate both names.
- Hosted-agent telemetry is **confirmed**: the platform injects `APPLICATIONINSIGHTS_CONNECTION_STRING`. `AppDependencies` hold the GenAI spans (89 MAF, 64 LangGraph) with `gen_ai.operation.name` (`invoke_agent`, `chat`, `execute_tool`), `gen_ai.agent.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`; `AppRequests` named `invoke_agent` come from role `agentsv2`; `AppGenAIContent` holds the message and tool-call content.

Next: [10 - Enterprise posture and scale](./10-enterprise-posture-and-scale.md) →

---

*Last updated: 2026-10-15*
