[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 05 Troubleshooting

# 05 - Troubleshooting

<p>
<img src="./assets/icons/api-management.svg" width="40" alt="API Management"/>&nbsp;
<img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway"/>&nbsp;
<img src="./assets/icons/foundry-agent-service.svg" width="40" alt="Foundry Agent Service"/>&nbsp;
<img src="./assets/icons/container-apps.svg" width="40" alt="Container Apps"/>&nbsp;
<img src="./assets/icons/key-vault.svg" width="40" alt="Key Vault"/>&nbsp;
<img src="./assets/icons/entra-id.svg" width="40" alt="Microsoft Entra ID"/>&nbsp;
<img src="./assets/icons/log-analytics.svg" width="40" alt="Log Analytics"/>
</p>

![version](./assets/badges/version.svg) ![live-tested](./assets/badges/live-tested.svg) ![Public preview](./assets/badges/public-preview.svg) ![regions](./assets/badges/regions-aigw.svg)

A symptom-first guide for the failures you are most likely to hit while deploying and running the landing zone. Start with the quick-triage table, jump to the product section for detail, and use the escalation package at the bottom if you still need help.

## Browser demo console

> [!IMPORTANT]
> The console is deployed with [limited live checks](./04-testing.md#live-follow-up-2026-10-16), not a completed browser acceptance matrix. Do not use the earlier script evidence as proof of console sign-in, RBAC or every workflow.

| Symptom | Check / remedy |
|---|---|
| Preprovision stops on context | Match the intended azd environment's `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` to `az account show`; use tenant-explicit sign-in per [03 Phase 0](./03-deployment.md#phase-0---authenticate-to-the-right-tenant). Do not bypass the gate. |
| `-o was unexpected at this time` followed by `Cannot check the console enterprise application` | Windows `az.cmd` can reinterpret parentheses in a JMESPath argument such as `length(@)` as batch syntax. The console hook uses `[0].id` instead. With the corrected hook, rerun `azd provision`; stored app-registration settings are reused, so no app or environment reset is needed. |
| Cannot resolve deployer / service-principal login rejected | Sign in to Azure CLI as a **human** in the intended tenant. Setup resolves `AZURE_PRINCIPAL_ID` from that user; an app/client ID is not a user object ID. |
| App/credential creation denied or auth inputs blank | Directory permissions to create/manage a separate single-tenant Entra app/credential are required. Verify setup populated `DEMO_CONSOLE_CLIENT_ID`, `DEMO_CONSOLE_ALLOWED_USER_ID`, and `DEMO_CONSOLE_CLIENT_SECRET` without printing the secret. Azure RBAC alone does not grant directory permissions. |
| Redirect URI mismatch / sign-in loop | Check the console app (not the gateway app), target tenant and provisioned URL; rerun `azd provision` to configure the redirect in postprovision, then `azd deploy demo-console`. |
| `401` at `/.auth/login/aad/callback` / ID token not enabled | Easy Auth requests the hybrid `code id_token` flow. The console Entra app must enable **ID tokens** under Authentication; implicit access-token issuance is not required. The provisioning hooks set `--enable-id-token-issuance true` for new apps and existing apps when configuring the callback. Keep the single-tenant setting and deployer allowlist unchanged. Retry sign-in after correcting the app setting. |
| Signed in but denied | Use the deploying human's account. Easy Auth enforces the tenant and deployer allowlist; backend checks ACA's trusted `X-MS-CLIENT-PRINCIPAL-ID` and rejects conflicting claims when supplied. Do not require the full App Service-style claims header on ACA. The JSON `auth_reason` and categorical `console_access_denied` log identify missing identity, configuration, provider, owner, or tenant mismatches without revealing principal IDs or tokens. A second same-tenant user is not automatically allowed. |
| `auth_reason: unexpected_identity_provider` after Entra sign-in | Update/redeploy the console's provider handling: Entra's `aad` and `azureActiveDirectory` names are aliases, while the full principal's `auth_typ` is an authentication type, not an identity-provider name. Do not compare all of these fields to the single literal `aad`, and do not remove the tenant/deployer-ID checks to get past this error. |
| Console loads, but browser `POST /api/run` returns `403` without reaching app logs | Easy Auth has its own cookie-based CSRF check before FastAPI. The console auth configuration explicitly includes only its HTTPS `consoleUrl` in `login.allowedExternalRedirectUrls`. Check that value against the browser origin; `azd provision` applies this infrastructure setting, while `azd deploy demo-console` only updates the application. Keep the backend exact-origin/custom-header checks and deployer allowlist; do not disable CSRF or enable wildcard CORS. [Easy Auth CSRF behavior](https://learn.microsoft.com/azure/app-service/overview-authentication-authorization#mitigation-of-cross-site-request-forgery). |
| Expired console app secret | Clear local `DEMO_CONSOLE_CLIENT_SECRET`, provision to append a new credential, then deploy the console. See [rotation](./03-deployment.md#console-secret-expiry-rotation-and-cleanup). Do not delete all app credentials blindly. |
| Console URL inaccessible in isolated mode | `NETWORK_ISOLATION=true` uses the internal ACA environment. Browser needs VNet/VPN access and private DNS; signing in does not create network reachability. |
| Hosted-agent request denied | Check **console managed identity** has **Azure AI User** at the Foundry **project** scope and allow RBAC propagation time. This is not the hosted agent's instance identity. |
| Authenticated APIM direct check denied | Check console identity's **Cognitive Services User** at Foundry **account** scope and accepted audience `https://cognitiveservices.azure.com`. S2's deliberate no-credential request should still return 401. |
| Tier key read fails | Check **Key Vault Secrets User** for the console identity, configured secret name and vault network reachability. `AIGW_KEY_DELIVERY=env` is an explicit demo-only opt-in delivered through an ACA secret; never paste the key into the browser. |
| Log query denied / empty | Check **Log Analytics Reader** at workspace scope. Query 01-11 is last-hour/max-200 bounded; empty data reports `not_run`. Wait for ingestion or generate confirmed demo traffic; query 04 needs a matching trace ID. |
| Workbook reports missing `DurationMs`, `PromptMessages`, or unset `traceId` | Deploy the corrected workbook, not just the console image. APIM gateway latency is `TotalTime`, while App Insights uses `DurationMs`; LLM messages may be `RequestMessages`/`ResponseMessages`. Workbook panels now bind the maintained saved KQL, and the trace input is optional (blank = recent hops). Reload the saved workbook from `WORKBOOK_ID`; discard an unsaved stale editing session. |
| Workbook token charts show zero while the detail table has tokens, or the X-axis contains a JSON timestamp array | The chart received `make-series` dynamic arrays instead of scalar points. Expand timestamp/token arrays **together** with `mv-expand TimeGenerated to typeof(datetime), Tokens to typeof(long)`. Bind one numeric `Tokens` column, grouped by a `/ input` or `/ output` `Series`; do not treat parsing an array in a test as proof that the portal receives numeric columns. |
| Token chart fails to parse at `)` after adding the selected start/end | Workbook KQL parameters already expand to datetime expressions. Use `{TimeRange:start}` / `{TimeRange:end}` directly; `datetime({TimeRange:start})` creates invalid nested syntax. Test Workbook-style expansion, not a raw ISO string substituted by a helper. |
| Time range label changes but the graph still fits only the traffic hours | Filter source events before joins/aggregation, then fill the selected start/end/grain with `make-series`. Expand to typed scalar points for the chart; sparse `summarize` results alone allow the time axis to shrink. Keep the existing `timeContextFromParameter` binding. |
| Seven-day chart loses early points or totals after flattening | A detail-table `take 200` was applied after point expansion. Limit intermediate **series** before `mv-expand` and retain every bucket; four series at three-hour intervals require **224** points over seven days. |
| Trace input appears to leave other panels unchanged | Expected: it filters only Trace investigation's timeline and hosted-agent content. The time range applies globally. Console S5 is a separate fixed one-hour query window; it does not inherit workbook parameters. |
| Agent answered but expected tool/audit is absent | Response success proves transport/protocol only. An agent may choose another/no tool; a response-header trace ID does not prove propagation. Verify source logs and query 04. |
| Changing gateway dropdown did not reroute agent / display differs from logs | Expected: dropdown changes **direct checks only**. Agent routing is deployed `HOSTED_DEFAULT_GATEWAY`; console display is a **provisioning snapshot**, not live discovery. Change `AGENT_DEFAULT_GATEWAY`, reprovision to sync console config, and redeploy agents. Agent-only deploy can leave the snapshot stale. |
| S1 is green but readiness was not checked | Expected: console S1 invokes Responses only; it does **not** issue a readiness GET. Verify readiness separately if required. |
| S5 is green but rows do not prove the intended audit claim | Expected: “passed” means a fixed query returned rows. Inspect those rows yourself; it is not an automatically validated audit assertion. |
| Write button does not run / tool arguments rejected | Confirm the specific direct write or agent submission. Refresh live MCP discovery and inspect its `inputSchema`/JSON args; no writes run automatically. Use disposable data. |
| Burst has no 429 | `not_run`, not a pass: the bounded 1-120 calls, concurrency ≤8, did not observe throttling. Inspect the selected gateway's response/logs; do not attribute policy origin from a 429 alone. |
| REST / denied-tool / OBO / ACA comparison unavailable | Direct REST and denied-tool probe are APIM-only; tier parity is not implemented. OBO and optional ACA agent comparison are manual/unavailable unless explicitly deployed. Do not replace them with fake results. |
| Console app remains after `azd down` | Expected: Entra apps/credentials are not resource-group resources. Manually clean up the console app/credentials in the intended tenant and retire secret-bearing local azd state. |

Keep tokens, keys, credentials, cookies and populated azd environment values out of screenshots, issue text and escalation logs. Inspect only redacted details when sharing failures.

## Decision tree

[![Troubleshooting decision tree](./assets/troubleshooting-decision-tree.png)](./assets/troubleshooting-decision-tree.png)

<sub>Editable source: [`assets/troubleshooting-decision-tree.drawio`](./assets/troubleshooting-decision-tree.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

## Quick triage

| Where | Symptom | Likely cause | Fix |
|---|---|---|---|
| <img src="./assets/icons/ai-gateway.svg" width="20" alt="AI Gateway"/> **AI Gateway tier** <img src="./assets/badges/public-preview.svg" alt="Public preview"> | Provisioning fails with `NoAvailableScaleGroups`, `InvalidResourceType` or a missing sku | The subscription is not registered for the `AIGatewayPreview` feature, or the region is wrong | Run the [feature registration](./02-prerequisites.md#register-the-ai-gateway-preview-feature) and re-register the provider; use `eastus2` or `swedencentral` |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt="AI Gateway"/> **AI Gateway tier** | Provisioning fails with "region not allowed" | The AI Gateway tier is public preview in **East US 2 and Sweden Central only** | Set `AI_GATEWAY_TIER_LOCATION` to `eastus2` or `swedencentral`; keep the rest of the landing zone wherever you like |
| <img src="./assets/icons/api-management.svg" width="20" alt="API Management"/> **APIM v2** | 401 from the gateway | Token audience is wrong, or the token is missing | Request a token for `api://<GATEWAY_APP_CLIENT_ID>` (or `https://cognitiveservices.azure.com`, both are accepted) |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt="AI Gateway"/> **AI Gateway tier** | 401 from the gateway | `api-key` missing, wrong, or revoked | Re-read the runtime key from Key Vault; check `keyVaultUri` and `AIGW_RUNTIME_KEY_SECRET_NAME` |
| <img src="./assets/icons/foundry-models.svg" width="20" alt="Foundry Models"/> **Foundry Models** | 404 "unknown model" / deployment not found | `MODEL_DEPLOYMENT_NAME` does not match the deployed model name | Align the variable with the deployment name (the demo targets `gpt-5.5` GlobalStandard) |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt="Foundry Agent Service"/> **Hosted agents** | Error mentioning protocol `1.0.0` | Agent declared the old protocol | Use `responses` protocol version `2.0.0` in the agent manifest and `azure.yaml` |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt="Foundry Agent Service"/> **Hosted agents** | Import error for a host class at startup | Unpinned or missing packages; missing `hosting` extra; requirements installed without `--pre` | Install the pinned `requirements.txt` with `--pre`; LangGraph needs `langchain-azure-ai[hosting,opentelemetry]` |
| <img src="./assets/icons/key-vault.svg" width="20" alt="Key Vault"/> **Key Vault** | `ForbiddenByConnection` or access denied reading the runtime key | Identity lacks **Key Vault Secrets User** (grant it to the hosted agent's **instance identity**), or a policy forces Key Vault public access off | See [the Key Vault entry](#hosted-agent-gets-forbiddenbyconnection-from-key-vault) |
| <img src="./assets/icons/log-analytics.svg" width="20" alt="Log Analytics"/> **Log Analytics** | Query 11 returns no rows | Telemetry not yet flowing; the tier writes `AppRequests`, not `ApiManagementGatewayLlmLog` | See the Log Analytics section below and [doc 09](./09-monitoring-and-audit.md) |

> [!TIP]
> Most "it worked yesterday" reports are an expired `az` or `azd` login, a rotated runtime key, or a changed tenant. Check the identity you are running as before debugging anything else: `az account show` and `azd auth login --check-status`.

## <img src="./assets/icons/api-management.svg" width="28" alt="API Management"/> API Management (v2 lane)

| Symptom | Cause | Fix |
|---|---|---|
| 401 on `/llm/openai/v1/...` | `validate-azure-ad-token` rejected the token (audience, issuer, expired) | Decode the token (`aud`, `iss`, `exp`) and compare with the policy's accepted audiences; both `{{gateway-audience}}` and `https://cognitiveservices.azure.com` are accepted |
| 403 JSON-RPC `-32601` from an MCP path | Tool name not in the MCP policy allow-list | Add the tool to the allow-list in `infra/policies/mcp-api-policy.xml` (see [doc 08](./08-tools-apim-mcp-topology.md)) |
| 429 with `Retry-After` | `llm-token-limit` (`TOKEN_LIMIT_TPM_PER_AGENT`, default 20000) or MCP rate limit (120 calls per 60 s per validated `azp`) | Expected under load; raise the named value or reduce concurrency |
| 413 on MCP call | Payload guard in the hardened MCP policy | Send a smaller request body |
| Tool response missing or truncated | A policy touched `context.Response.Body` | Remove it. MCP policies must be **inbound-only**; reading the response body breaks streaming. See [Microsoft Learn: MCP server overview](https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview) |
| Tool backend sees no human identity | Caller used `client_credentials` (no `scp`), so `x-gw-user-oid` is intentionally empty | Expected for autonomous agents; see [doc 07](./07-identity-auth-traceability.md) |

> [!WARNING]
> Client-supplied `x-gw-*` headers are deleted by the identity-headers fragment before gateway-derived values are set. If you see forged identity in audit logs, the fragment is not included on that API.

## <img src="./assets/icons/ai-gateway.svg" width="28" alt="AI Gateway"/> AI Gateway tier ![Public preview](./assets/badges/public-preview.svg)

The tier is preview with no SLA, restricted to East US 2 and Sweden Central. It is an `Microsoft.ApiManagement/service` resource with sku `AIGateway` at API version `2025-09-01-preview`, and it requires the `AIGatewayPreview` feature registration. The resource shapes in this repo were validated live on 2026-10-02, but they can still change. `Microsoft.ApiManagement/aigateways` and `2026-05-01-preview` do not work. Source: [AI Gateway overview](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-overview).

| Symptom | Cause | Fix |
|---|---|---|
| `NoAvailableScaleGroups` / `InvalidResourceType` | Feature not registered, or the wrong resource type or API version was used | Register `AIGatewayPreview`, re-register `Microsoft.ApiManagement`, and deploy `service` with sku `AIGateway` at `2025-09-01-preview` |
| Region not allowed <img src="./assets/badges/public-preview.svg" alt="Public preview"> | Wrong location | `AI_GATEWAY_TIER_LOCATION` = `eastus2` or `swedencentral` |
| Model call fails with a deployment-not-found error | Provider `modelName` does not equal the Foundry deployment **name**, or the request `model` does not equal the model alias name | Use `chat` for all three |
| Tool server returns a URL error | The OpenAPI tool server has no absolute `servers[0].url` | Bicep injects it; keep the OpenAPI document's server URL absolute |
| 401 with a runtime key | Key copied from another gateway, or regenerated | The key is **gateway-scoped**. Re-create it and store it in the Key Vault secret `aigw-runtime-key` |
| Runtime key not in Key Vault | `postprovision` could not read the key (strict mode or `listSecrets` parse, fixed in v1.2) | Re-run `azd provision`, or create a key named `agents` in the portal at `https://ai.gateway.azure.com` and store it in Key Vault |
| Query 11 or the portal shows no LLM log rows | The tier does not write `ApiManagementGatewayLlmLog` | Query `AppRequests` (`AppRoleName` `aigw-<name> East US 2`; tokens in `Measurements`); MCP calls are also in `ApiManagementGatewayMCPLog` |
| Model call returns backend auth error | Backend auth (None / API key / OAuth2 / Managed identity) misconfigured, or the managed identity lacks the Foundry User role | Fix the backend credential; grant the gateway's managed identity the Foundry User role on the Foundry resource |
| Tool backend audit shows `agent_principal: null` | By design: the tier authenticates a runtime key, not an Entra principal | Read `caller` (`aigw-runtime-key:agents`) and `gateway` (`aigateway`) instead |

## <img src="./assets/icons/foundry-agent-service.svg" width="28" alt="Foundry Agent Service"/> Foundry hosted agents

Hosted agents run the official hosts (no fallback server). Hosted agents are GA; several sub-features (long-running execution, A2A, routines, durable state) are preview. Container contract and limits: [doc 06](./06-hosted-agents-explained.md).

| Symptom | Cause | Fix |
|---|---|---|
| Container starts but never becomes ready | `GET /readiness` does not return 200, or the app is not listening on port **8088** | Bind `0.0.0.0:8088` over plain HTTP; the platform terminates TLS |
| Protocol 1.0.0 error | Old protocol selected | `responses` 2.0.0 |
| Host class import error | Packages not pinned, or the hosting extra missing | Use the pinned requirements; see the package check below |
| Cold start after idle | Sessions scale to zero after the idle timeout (2 to 60 minutes, default 15) | Expected; first call after idle is slower |
| `azd` deploy of the agent fails | Old `azure.ai.agents` extension | Upgrade to `>=1.0.0-beta.18` (see [azd triage](#azd-triage)) |
| Private registry pull fails | Projects created after 2026-06-25 require a private Azure Container Registry | Use ACR with the project identity granted pull access |
| Host crashes with `PermissionError: /app/.agentserver` | The container runs as `app` but `/app` is owned by root | The Dockerfile must run `chown app:app /app` (already present in v1.2) |
| Hosted call returns HTTP 200 with `status: "failed"` and `error.code: "server_error"` (Agent Framework) | The agent could not reach its model, gateway or tools; the host reports failures inside the response body | Check the agent log stream; the usual causes are the Key Vault entry below and an alias mismatch |
| LangGraph answers without using tools | The MCP server was unreachable; the agent logs `mcp_tools_unavailable` and continues without tools | Fix gateway reachability or credentials; this is by design, not a crash |
| Preview warnings at startup <img src="./assets/badges/public-preview.svg" alt="Public preview"> | The official hosts are pre-release | Informational; ignore |

### Hosted-agent package check

| Framework | Must be installed | Host class | Notes |
|---|---|---|---|
| Microsoft Agent Framework | `agent-framework-core`, `agent-framework-openai`, `agent-framework-foundry-hosting` (pre-release), `mcp` | `ResponsesHostServer` from `agent_framework_foundry_hosting` | Docker build uses `pip --pre` |
| LangGraph | `langchain-azure-ai[hosting,opentelemetry]`, `langchain`, `langchain-openai`, `langchain-mcp-adapters` | `ResponsesHostServer` from `langchain_azure_ai.agents.hosting` | The `hosting` extra provides the host class |

## <img src="./assets/icons/container-apps.svg" width="28" alt="Container Apps"/> Container Apps (tool backends)

| Symptom | Cause | Fix |
|---|---|---|
| `catalog-mcp` or `records-api` unhealthy | Wrong target port | They listen on **8080**; check ingress target port |
| MCP call returns 502 through the gateway | Backend revision not ready or scaled to zero with cold start | Check the revision in the Container Apps environment; retry |
| Empty audit lines | Console log table has no data yet | Allow a few minutes for ingestion; confirm `ContainerAppConsoleLogs_CL` has rows |
| Image pull failure | Registry identity lacks pull rights | Grant the app's managed identity `AcrPull` on the registry |

## <img src="./assets/icons/key-vault.svg" width="28" alt="Key Vault"/> Key Vault

| Symptom | Cause | Fix |
|---|---|---|
| `Forbidden` reading `aigw-runtime-key` | Missing RBAC | Assign **Key Vault Secrets User** to the hosted agent's **instance identity** (not the project identity) |
| Unsure which identity reads the secret | The runtime principal is the agent's instance identity, which exists only after `azd deploy` | `azd ai agent show <agent> --output json`, read `instance_identity.principal_id`; the `postdeploy` hook grants the role ([03](./03-deployment.md#key-delivery-and-the-postdeploy-hook)) |
| Secret not found | Wrong secret name | Align `AIGW_RUNTIME_KEY_SECRET_NAME` with the secret created by `postprovision` |
| `ForbiddenByConnection` | See the next section | See the next section |

### Hosted agent gets ForbiddenByConnection from Key Vault

<img src="./assets/icons/key-vault.svg" width="24" alt="Key Vault"/> The agent log shows a Key Vault 403 with `ForbiddenByConnection`, even though the role assignment exists. Hosted agents run **outside your VNet**, and when an organization policy disables Key Vault public network access, the vault firewall rejects them. This happened in the live run.

| Order | Fix | Notes |
|---|---|---|
| **1** | Confirm the role: `az role assignment list --scope <KEY_VAULT_ID> --assignee <instance principal id>` | Rules out a plain RBAC gap. The `postdeploy` hook is not live-verified, so grant manually if it shows `NOT FOUND` or `FAILED`. |
| **2** | **Proper fix:** `azd env set NETWORK_ISOLATION true`, then `azd provision` and `azd deploy` | Adds a Key Vault private endpoint and agent subnet injection. ![static-only](./assets/badges/static-only.svg) what-if validated only; you also need in-VNet access for `azd deploy` and the Key Vault data plane. |
| **3** | **Demo-only compromise:** `azd env set AIGW_KEY_DELIVERY env`, then `azd provision` and `azd deploy agent-maf agent-langgraph` | The runtime key is stored in **plaintext** in `.azure/<env>/.env` and the agent configuration. The agent logs the WARNING `aigw_runtime_key_source source=env`. |

> [!WARNING]
> Option 3 trades security for convenience. Use it only in a disposable demo environment and rotate the AI Gateway runtime key afterwards. In `keyvault` mode the agent also falls back to a non-empty `AIGW_RUNTIME_KEY` when the Key Vault read fails, so a stale value in the environment can mask this problem.

## <img src="./assets/icons/entra-id.svg" width="28" alt="Microsoft Entra ID"/> Microsoft Entra ID

| Symptom | Cause | Fix |
|---|---|---|
| `AADSTS` audience error | Requested scope does not match the gateway app | Use `api://<GATEWAY_APP_CLIENT_ID>/.default` |
| No human identity on tool calls | Autonomous (client_credentials) flow | Use OBO via `samples/obo-client/invoke_as_user.py --agent maf\|langgraph` for user-attributed calls |
| Cannot find agent sign-ins | They are an `agentSignIn` attribute on existing sign-in logs, not a new table | See [Agent sign-in and audit logs](https://learn.microsoft.com/en-us/entra/agent-id/sign-in-audit-logs-agents) |
| Agent identity limit worry | The 250-identities limit applies to non-Microsoft platforms using app-only client credentials; Foundry is exempt | See [Agent ID FAQ](https://learn.microsoft.com/en-us/entra/agent-id/faq) |

## <img src="./assets/icons/log-analytics.svg" width="28" alt="Log Analytics"/> Log Analytics

| Symptom | Cause | Fix |
|---|---|---|
| Query 11 empty | No traffic yet, or telemetry lag | Query 11 reads `AppRequests` (tier) and `AppDependencies` (content safety); send traffic and wait a few minutes |
| Query 04 shows no gateway rows for a trace id | Gateway log rows carry no trace id | Expected; join on time and caller, or use the `AppRequests` rows |
| Query 09 error `ErrorMessage` not found | `ApiManagementGatewayLogs` has no `ErrorMessage` column | Use `LastErrorMessage` and `LastErrorReason` (fixed in v1.2) |
| No `ApiManagementGatewayMCPLog` rows | Diagnostic category `GatewayMCPLogs` not enabled | Enable categories `GatewayLogs`, `GatewayLlmLogs`, `GatewayMCPLogs` ([monitor MCP servers](https://learn.microsoft.com/en-us/azure/api-management/monitor-mcp-servers)) |
| Trace id missing in tool audit | Caller did not send `traceparent` | The agents generate one if absent; confirm the gateway preserved it (`exists-action="skip"`) |
| `run_audit_queries.py` auth error | CLI credential for the wrong tenant | `az login --tenant <TENANT_ID>` and retry |

## azd triage

| Step | | Action | Validation |
|---|---|---|---|
| 1 | <img src="./assets/icons/subscription.svg" width="24" alt="subscription"/> | `azd env get-values` and confirm location, subscription and `AI_GATEWAY_MODE` | - [ ] Values are what you intended |
| 2 | <img src="./assets/icons/azure-devops.svg" width="24" alt="azd"/> | `azd extension list` and confirm `azure.ai.agents` is `>=1.0.0-beta.18` <img src="./assets/badges/public-preview.svg" alt="Public preview"> | - [ ] Extension current |
| 3 | <img src="./assets/icons/resource-group.svg" width="24" alt="resource group"/> | `azd provision --preview` then `azd provision` | - [ ] Fails with a specific resource error, not auth |
| 4 | <img src="./assets/icons/foundry-agent-service.svg" width="24" alt="agent"/> | `azd deploy agent-maf` (or `agent-langgraph`) | - [ ] Agent version reaches the ready state |

## Escalation package

If you need help, collect these (never include secrets):

- [ ] `azd env get-values` output with secret-like values redacted.
- [ ] Your ids file (`demo-ids.local.json`) **without** keys or tokens.
- [ ] The exact error text and HTTP status.
- [ ] The APIM request id or `x-gw-request-id` from the failing call.
- [ ] The `traceparent` header used for the request.
- [ ] Whether `AI_GATEWAY_MODE`, `AGENT_DEFAULT_GATEWAY` and `AI_GATEWAY_TIER_LOCATION` were set intentionally.

> [!NOTE]
> For the AI Gateway tier (preview, no SLA) also record the management API version (`2025-09-01-preview`), the region, and whether the `AIGatewayPreview` feature shows `Registered`.

---

Next: [06 - Hosted agents explained](./06-hosted-agents-explained.md) →

*Last updated: 2026-10-15*
