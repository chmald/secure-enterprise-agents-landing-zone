[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 07 Identity, auth and traceability

# 07 - Identity, Auth and Traceability

<p>
<img src="./assets/icons/entra-id.svg" width="40" alt="Microsoft Entra ID"/>&nbsp;
<img src="./assets/icons/entra-workload-id.svg" width="40" alt="Entra Workload ID"/>&nbsp;
<img src="./assets/icons/managed-identity.svg" width="40" alt="Managed identity"/>&nbsp;
<img src="./assets/icons/app-registrations.svg" width="40" alt="App registrations"/>&nbsp;
<img src="./assets/icons/api-management.svg" width="40" alt="API Management"/>&nbsp;
<img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway"/>&nbsp;
<img src="./assets/icons/foundry-agent-service.svg" width="40" alt="Foundry Agent Service"/>
</p>

![GA](./assets/badges/ga.svg) ![Preview](./assets/badges/preview.svg) ![Public preview](./assets/badges/public-preview.svg) ![DIY](./assets/badges/diy.svg) ![version](./assets/badges/version.svg) ![live-tested](./assets/badges/live-tested.svg)

This is the central page of the demo. It answers the question enterprise security teams ask first: **when an agent calls a model or a tool, who is that, and can we prove it afterwards?** It explains how identity is established for a hosted agent, what the gateway can and cannot prove, how identity and trace context reach the tool backends, and how to correlate everything in Log Analytics. It closes with the five design questions you should settle before scaling to thousands of agents.

## At a glance

| | Topic | One-line answer |
|---|---|---|
| <img src="./assets/icons/entra-workload-id.svg" width="24" alt="Entra Workload ID"/> | Agent identity | The runtime principal of a hosted agent is its **instance identity** (distinct from the blueprint and the project identity), found live on 2026-10-02 |
| <img src="./assets/icons/entra-id.svg" width="24" alt="Microsoft Entra ID"/> | User-invoked agents | **On-behalf-of (OBO)**: the agent acts as the user, token carries both |
| <img src="./assets/icons/app-registrations.svg" width="24" alt="App registrations"/> | Autonomous agents | **client_credentials**: the agent acts as itself |
| <img src="./assets/icons/api-management.svg" width="24" alt="API Management"/> | APIM Standard v2 | **Validates** the token and derives `x-gw-*` headers; never exchanges tokens |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt="AI Gateway"/> | AI Gateway tier | ![Public preview](./assets/badges/public-preview.svg) Gateway-scoped runtime key; **no per-identity validation** |
| <img src="./assets/icons/log-analytics.svg" width="24" alt="Log Analytics"/> | Traceability | W3C `traceparent` carried end to end; correlation across systems is **DIY** ![DIY](./assets/badges/diy.svg) |

## The identity model

### Browser console is a separate caller, not OBO

The new console has a **separate single-tenant Entra app**. ACA Easy Auth requires sign-in and allowlists the deploying human's object ID; FastAPI independently verifies the platform-injected principal ID and rejects conflicting owner/tenant claims when supplied. This controls **browser access**, not delegation. Downstream requests use the **console backend managed identity**: Azure AI User (Foundry project), Cognitive Services User (Foundry account; APIM token audience `https://cognitiveservices.azure.com`), Log Analytics Reader (workspace), and Key Vault Secrets User (vault). On the tier, direct checks use a runtime key, not an Entra caller principal.

**Platform header contract:** [Container Apps authentication](https://learn.microsoft.com/azure/container-apps/authentication#access-user-claims-in-application-code) injects `X-MS-CLIENT-PRINCIPAL-ID` after authentication and prevents external callers from setting trusted identity headers. The console runs behind that mandatory Easy Auth boundary; it does not authenticate raw client headers on a standalone public server. If the full Base64 claims header is present, malformed or conflicting claims still fail closed. Tenant validation is enforced by the configured single-tenant Easy Auth issuer, not by assuming ACA always supplies a `tid` header.

Entra provider identifiers `aad` and `azureActiveDirectory` refer to the same configured provider. The full principal's `auth_typ` describes the claims identity's authentication type (which can be a federation authentication type); it is not a provider identifier. Access decisions use the platform-validated deployer ID and any supplied owner/tenant claims, not an assumed `auth_typ == "aad"` string.

Browser POSTs pass two CSRF checks: Easy Auth's session-cookie check and the backend's exact-origin plus custom-header check. The auth configuration explicitly lists only the console's HTTPS URL in `login.allowedExternalRedirectUrls`, so the platform recognizes the browser origin before forwarding the request. No other origin or wildcard CORS is enabled, and the Entra tenant/deployer allowlist still applies.

The console does not forward the browser's credentials, perform OBO, or impersonate a hosted agent. Agent-to-gateway calls still use the deployed agent identity/configuration below. Header trace IDs are advisory; inspect logs to verify propagation. The OBO sample remains manual/unavailable unless explicitly deployed. See the [limited console live checks and remaining acceptance work](./04-testing.md#live-follow-up-2026-10-16); the earlier identity evidence does not validate this new caller. App-secret rotation and manual Entra cleanup after `azd down`: [03](./03-deployment.md#console-secret-expiry-rotation-and-cleanup).

| Console direct-call path | Credential used | Key Vault dependency |
|---|---|---|
| APIM Standard/Premium v2 | Short-lived Entra access token from the console managed identity, audience `https://cognitiveservices.azure.com`; APIM validates the bearer token. | No AI Gateway runtime-key read. APIM uses its own managed identity for the Foundry model backend. |
| AI Gateway tier | Gateway-scoped runtime key sent server-side in `api-key`. | Default `keyvault` mode reads the secret with the console identity. Explicit demo-only `env` mode reads `AIGW_RUNTIME_KEY` from an ACA secret reference instead. The key remains in secret-bearing local azd state too. |

[![Identity and runtime-key flow](./assets/identity-token-flow.png)](./assets/identity-token-flow.png)

Foundry integrates with **Microsoft Entra Agent ID**. A hosted agent is not just a container; it has an identity that other systems can authorize and audit. Source: [Agent identity concepts in Foundry](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-identity).

| Principal | What it is | Used for |
|---|---|---|
| **Blueprint** | The Entra Agent ID blueprint created when the agent is registered | Registration; **not** the identity that calls downstream services in the live run |
| **Foundry project identity** | The managed identity of the Foundry project | Project-level operations; **not** the agent's effective runtime identity |
| **Instance identity principal** | A per-agent identity created when the agent is deployed; returned by `azd ai agent show <agent> --output json` as `instance_identity.principal_id` | The **effective runtime identity**: it obtains tokens for the model, the gateway and Key Vault. Stable across agent versions |

### The runtime principal is the instance identity

The v1.2 live run (2026-10-02) settled which identity a hosted agent really uses. Two consequences follow:

> [!IMPORTANT]
> **Bicep cannot grant the instance identity anything.** It only exists after `azd deploy`, so the grant has to happen afterwards. It needs **Key Vault Secrets User** on the demo vault to read the AI Gateway runtime key. The `postdeploy` hook (`infra/hooks/postdeploy-agents.ps1`) does this idempotently for each agent ([03](./03-deployment.md#key-delivery-and-the-postdeploy-hook)); it is covered by offline tests but was granted by hand in the live run, so treat it as not live-verified.

| Gateway lane | Role needed by the instance identity | Why |
|---|---|---|
| APIM Standard v2 | **None** | APIM validates the bearer token (audience `https://cognitiveservices.azure.com`) and reaches Foundry with its own managed identity |
| AI Gateway tier | **Key Vault Secrets User** on the vault (or `AIGW_KEY_DELIVERY=env`) | The agent reads the gateway-scoped runtime key from Key Vault |

When `FOUNDRY_HOSTING_ENVIRONMENT` is set, the agent code builds `ManagedIdentityCredential(client_id=FOUNDRY_AGENT_INSTANCE_CLIENT_ID)`; the platform injects both variables.

### Key Vault access under network policy

Granting the role is not always enough. In the live subscription, an organization policy forced Key Vault public network access off. Hosted agents run **outside your VNet**, so the vault returned `ForbiddenByConnection` even with the role in place.

| Option | What it does | Status |
|---|---|---|
| **Network isolation mode** (`NETWORK_ISOLATION=true`) | Adds a Key Vault private endpoint and agent subnet injection, so the read stays on the private network. This is the proper fix. | ![static-only](./assets/badges/static-only.svg) what-if validated only |
| `AIGW_KEY_DELIVERY=env` | The runtime key is copied into the azd env and the agent configuration, so the agent never calls Key Vault. A demo-only compromise: the key is stored in plaintext in `.azure/<env>/.env`. | ![live-tested](./assets/badges/live-tested.svg) |
| Allow public access on the vault | Opens the vault to the internet | Blocked by the policy in the test subscription; not recommended |

> [!WARNING]
> `AIGW_KEY_DELIVERY=env` makes the runtime key readable by anyone who can read the agent configuration or your local azd env. Use it only for disposable demos. In `keyvault` mode the agent also falls back to a non-empty `AIGW_RUNTIME_KEY` when the vault read fails, logging the WARNING `aigw_runtime_key_source`. Troubleshooting steps: [05](./05-troubleshooting.md#hosted-agent-gets-forbiddenbyconnection-from-key-vault).

## OBO vs client credentials

The token flow depends on whether a human is in the loop. Both flows are Entra Agent ID flows.

| | **On-behalf-of (OBO)** | **client_credentials** (autonomous) |
|---|---|---|
| Use when | A user invokes the agent | A schedule, event or system invokes the agent |
| Acts as | The user, through the agent | The agent itself |
| Token has | `sub` + `scp` (delegated), agent as actor | App-only token; no `scp`, no human subject |
| Gateway sees | `x-gw-user-oid` populated | `x-gw-user-oid` empty |
| Audit shows | `human_principal` **and** `agent_principal` | `agent_principal` only |
| In this repo | `samples/obo-client/invoke_as_user.py --agent maf\|langgraph` | Default scripted calls |
| Learn | [Agent OBO flow](https://learn.microsoft.com/en-us/entra/agent-id/agent-on-behalf-of-oauth-flow) | [Autonomous app flow](https://learn.microsoft.com/en-us/entra/agent-id/agent-autonomous-app-oauth-flow) |

> [!NOTE]
> **Neither APIM nor an API key performs OBO.** OBO is an Entra token exchange done by the caller (or the agent runtime). The gateway only receives and validates the result.

## Actor facets in the token

Agent tokens carry **actor facet** claims that say what kind of principal is acting. Source: [Agent token claims](https://learn.microsoft.com/en-us/entra/agent-id/agent-token-claims).

| Claim | Meaning | Values this demo reads |
|---|---|---|
| `xms_act_fct` | **Actor** facets: what is acting. Multi-valued | `11` = AgentIdentity, `13` = AgentIDUser |
| `xms_sub_fct` | **Subject** facets: what the token is about | Not used for headers |
| `xms_tnt_fct` | **Tenant** facets | Not used for headers |

The APIM fragment joins the `xms_act_fct` values into the header `x-gw-actor-facets`, so a tool backend can tell an agent identity from an agent user without parsing a JWT.

## APIM validates, it does not exchange

> [!WARNING]
> **APIM validates only.** The `validate-azure-ad-token` policy checks that a token is genuine, current and meant for this gateway. It does **not** mint, exchange or downscope tokens, and an APIM **subscription key** or Foundry **API key** is a metering and entitlement mechanism, not an identity. If a downstream system needs the caller's identity, it must come from the validated token (the demo's `x-gw-*` headers), never from a key.

Why this matters: three identity patterns exist for a gateway in front of tools, and each has a different answer to "who does the backend see?"

| Pattern | Backend sees | Trade-off |
|---|---|---|
| **A. Managed identity** (gateway authenticates to the backend as itself) | The APIM service principal | Human and agent attribution is lost |
| **B. Caller-token passthrough / derived headers** (this demo, APIM v2 lane) | The real user or workload principal (as `x-gw-*` headers derived from the validated token) | APIM backend auth `none`; subscription key still handles metering |
| **C. Split plane** (some traffic goes around the gateway) | Whatever the direct route supplies | Direct route bypasses APIM quota and metering |

## `validate-azure-ad-token` vs `validate-jwt`

Both policies run on all APIM tiers. Source: [validate-azure-ad-token](https://learn.microsoft.com/en-us/azure/api-management/validate-azure-ad-token-policy) · [validate-jwt](https://learn.microsoft.com/en-us/azure/api-management/validate-jwt-policy).

| | `validate-azure-ad-token` | `validate-jwt` |
|---|---|---|
| Scope | Entra-specific convenience wrapper | Generic, any identity provider |
| Configuration | Tenant id, accepted client app ids, audiences | OpenID config URL, issuers, audiences, required claims |
| Entra ID for customers | Not supported (<img src="./assets/badges/public-preview.svg" alt="Public preview"> limitation) | Use it for issuers outside the wrapper's scope |
| Used here | **Yes**, in the LLM, MCP and records API policies | Alternative if you add a non-Entra IdP |
| Backend credential | n/a (`authentication-managed-identity` is a separate policy for APIM-to-backend calls) | n/a |

The demo accepts two audiences: the gateway app (`api://<GATEWAY_APP_CLIENT_ID>`, from `{{gateway-audience}}`) and `https://cognitiveservices.azure.com` (the value `GATEWAY_AUDIENCE` carries in `azure.yaml`, so Foundry-native SDK token providers work unchanged).

## Gateway identity header contract

After validation, the shared `identity-headers` policy fragment first **deletes any client-supplied `x-gw-*` header**, then sets trusted values from token claims. Downstream services treat these headers as authoritative **only because** the fragment is attached on every API. The agents also strip `x-gw-*` from their own outbound requests (`strip_gateway_headers`).

| Header | Source | When set | Used for |
|---|---|---|---|
| `x-gw-agent-appid` | Token `azp` (or `appid`) | Always after validation | Which agent application called |
| `x-gw-agent-oid` | Token `oid` | Always after validation | Agent service principal object id |
| `x-gw-user-oid` | Token `oid` | **Only** when both `sub` and `scp` are present (delegated/OBO) | Which human the agent acted for |
| `x-gw-actor-facets` | Token `xms_act_fct`, joined | When present | Kind of actor |
| `x-gw-request-id` | `context.RequestId` | Always | Join key to APIM logs |
| `traceparent` | Caller | **Preserved** (`exists-action="skip"`), never overwritten | End-to-end correlation |
| `x-gw-caller` | AI Gateway tier | Only on the AI Gateway lane (value `aigw-runtime-key:agents`) | Label for the runtime key, **not** an identity |

> [!TIP]
> The fragment is the single place that turns a validated token into headers. When you add a new API behind the gateway, include the fragment, never copy claim logic.

## Audit record schema

Each tool backend (`catalog-mcp`, `records-api`) writes one JSON line per call. The agent and gateway fields come only from the headers above, and secrets are redacted by design.

| Field | Type | Notes |
|---|---|---|
| `event` | string | Always `tool_audit` |
| `timestamp` | ISO 8601 UTC | |
| `trace_id`, `span_id`, `traceparent` | string or null | Parsed from `traceparent`; null if absent or all-zero |
| `service` | string | `catalog-mcp` or `records-api` |
| `tool`, `operation` | string | Tool name and what it did |
| `decision`, `reason` | string | Allow/deny and why |
| `human_principal` | `{oid}` or null | From `x-gw-user-oid` |
| `agent_principal` | `{appid, oid, actor_facets}` | From the agent headers; fields null when absent |
| `gateway_request_id` | string or null | From `x-gw-request-id` |
| **`gateway`** (v1.1) | `apimv2` · `aigateway` · null | `aigateway` when `x-gw-caller` is present; `apimv2` when any other `x-gw-*` header is present; null with no gateway headers |
| **`caller`** (v1.1) | string or null | The `x-gw-caller` value, for example `aigw-runtime-key:agents` |
| `domain_profile` | string | Active profile name |
| `latency_ms`, `status_code` | number, int | |

<details><summary><b>Show: example audit records for both gateway lanes</b></summary>

APIM Standard v2 (OBO call, human and agent known):

```json
{"event":"tool_audit","timestamp":"2026-10-01T14:03:22.418+00:00","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7","traceparent":"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01","service":"catalog-mcp","tool":"check_availability","operation":"tools/call","decision":"allow","reason":"ok","human_principal":{"oid":"<USER_OBJECT_ID>"},"agent_principal":{"appid":"<AGENT_APP_ID>","oid":"<AGENT_OBJECT_ID>","actor_facets":"11"},"gateway_request_id":"<APIM_REQUEST_ID>","gateway":"apimv2","caller":null,"domain_profile":"manufacturing-field-ops","latency_ms":12.4,"status_code":200}
```

AI Gateway tier (runtime key, no per-identity validation):

```json
{"event":"tool_audit","timestamp":"2026-10-01T14:05:09.102+00:00","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7","traceparent":"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01","service":"catalog-mcp","tool":"check_availability","operation":"tools/call","decision":"allow","reason":"ok","human_principal":null,"agent_principal":{"appid":null,"oid":null,"actor_facets":null},"gateway_request_id":null,"gateway":"aigateway","caller":"aigw-runtime-key:agents","domain_profile":"manufacturing-field-ops","latency_ms":15.1,"status_code":200}
```

Values are illustrative. The shape is enforced by `tests/test_audit_record.py` and `tests/test_trace_propagation.py`.

</details>

## Standard v2 vs AI Gateway tier: what identity can you prove?

[![Gateway identity comparison](./assets/gateway-identity-comparison.png)](./assets/gateway-identity-comparison.png)

<sub>Editable source: [`assets/gateway-identity-comparison.drawio`](./assets/gateway-identity-comparison.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

| | Dimension | <img src="./assets/icons/api-management.svg" width="20" alt="API Management"/> APIM Standard v2 | <img src="./assets/icons/ai-gateway.svg" width="20" alt="AI Gateway"/> AI Gateway tier |
|---|---|---|---|
| | Status | ![GA](./assets/badges/ga.svg) | ![Public preview](./assets/badges/public-preview.svg) ![regions](./assets/badges/regions-aigw.svg) |
| | Runtime credential | Entra bearer token | Gateway-scoped `api-key` header |
| | Per-identity validation at runtime | **Yes** (`validate-azure-ad-token`) | **No** |
| | Human attribution (`human_principal`) | Yes, with OBO | No |
| | Agent attribution (`agent_principal`) | Yes, from validated claims | `null` |
| | What the audit shows | `gateway=apimv2`, `caller=null`, real principals | `gateway=aigateway`, `caller=aigw-runtime-key:agents`, `agent_principal=null` |
| | Per-agent quota | `llm-token-limit` keyed per agent | Gateway-level policy cards (token and request rate limits, IP filter, content safety) |
| | Telemetry | `ApiManagementGatewayLogs`, `...LlmLog`, `...MCPLog` | Application Insights `AppRequests` (tokens in `Measurements["gen_ai.usage.*"]`), `AppDependencies`, plus `ApiManagementGatewayMCPLog`; **no** `ApiManagementGatewayLlmLog` |
| | SLA | Per APIM tier | None (preview) |

> [!TIP]
> **Recommendation:** choose APIM Standard v2 whenever identity attribution is a requirement. Choose the AI Gateway tier when you want its managed model and tool governance and can accept that **the gateway proves possession of a key, not who is calling**. If you need both, run `AI_GATEWAY_MODE=both` and route identity-sensitive agents through the v2 lane. Learn: [AI Gateway overview](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-overview).

To obtain per-agent attribution on the AI Gateway tier you would have to add your own identity layer. The demo does not, and the audit makes the gap explicit.

## Trace propagation and correlation

[![Trace correlation](./assets/trace-correlation.png)](./assets/trace-correlation.png)

The agents create a W3C `traceparent` if the caller did not send one, forward it on every gateway call, and APIM preserves it. Tool backends parse it into `trace_id` and `span_id`, so one request can be followed from the client to the model call to the tool.

| Question | Query | Where |
|---|---|---|
| Who called which tool? | `01-who-called-which-tool.kql` | [doc 09](./09-monitoring-and-audit.md) |
| Show everything for one trace | `04-end-to-end-trace.kql` (pass `--trace-id`) | [doc 09](./09-monitoring-and-audit.md) |
| What did AI Gateway tier telemetry record? | `11-ai-gateway-tier-telemetry.kql` (`AppRequests`) | [doc 09](./09-monitoring-and-audit.md) |

> [!CAUTION]
> **Cross-system correlation is DIY.** There is no managed service that stitches Entra sign-in logs, gateway logs, tool logs and model telemetry together for you. The join key is the W3C `traceparent` trace id (plus `x-gw-request-id` for APIM), and the glue is KQL you own. OpenTelemetry GenAI semantic conventions (`invoke_agent`, `execute_tool`, `chat`) are still at "Development" status upstream, so expect attribute names to evolve. Agent sign-ins appear as an `agentSignIn` attribute on existing Entra sign-in logs ([Learn](https://learn.microsoft.com/en-us/entra/agent-id/sign-in-audit-logs-agents)), not as a new table.

## Foundry RBAC and API keys are not enough

| Mechanism | What it does | Why it does not solve attribution |
|---|---|---|
| Foundry RBAC | Controls who can manage and invoke resources | Authorizes a principal for a resource; says nothing about which agent called which downstream tool |
| Foundry / model API keys | Authenticate possession of a secret | Shared secret; no principal, no OBO, not attributable to a person or an agent |
| APIM subscription keys | Metering, product entitlement | Same: a metering handle, not identity |
| AI Gateway tier runtime key | Authenticates a client to the gateway | Gateway-scoped; all callers holding the key look identical |
| **Entra Agent ID token validated at the gateway** | Cryptographically bound to an agent (and user via OBO) | The only mechanism here that gives attributable identity |

## Licensing

| Capability | License needed |
|---|---|
| Base Entra Agent ID (agent identities, tokens, this demo's APIM v2 flow) | **No license** |
| Conditional Access, Identity Protection and Identity Governance **for agents** | **Microsoft Agent 365**, obtained through Microsoft 365 E7 or the Agent 365 add-on, **plus** Entra ID P1 or Microsoft 365 E3 |

Confirm current terms before purchase: [Agent ID licensing](https://learn.microsoft.com/en-us/entra/includes/licensing-agent-id).

## Runtime coverage parity

Not every agent you own runs in Foundry. The identity approach differs by where the agent runs.

| Runtime | Identity primitive | Gateway validation works? | Notes |
|---|---|---|---|
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt="Foundry Agent Service"/> **Foundry hosted agent** | Agent ID blueprint plus a per-agent instance identity (the runtime principal) | Yes (APIM v2 lane) | The reference path in this repo |
| <img src="./assets/icons/container-apps.svg" width="20" alt="Container Apps"/> **Self-hosted on Container Apps** | Managed identity or app registration you assign | Yes, if it obtains a token for the gateway audience | You own lifecycle and governance |
| <img src="./assets/icons/entra-id-governance.svg" width="20" alt="Entra ID Governance"/> **Microsoft Copilot Studio** | Entra Agent ID | Yes, as an Entra principal | Exempt from the 250 limit |
| <img src="./assets/icons/virtual-network.svg" width="20" alt="Other platforms"/> **Non-Microsoft platforms** | App-only client credentials | Yes (app-only token), but **no OBO and no actor-facet semantics** unless the platform supports Agent ID flows | Subject to the 250 limit |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt="AI Gateway"/> **Any agent via AI Gateway tier** | Runtime key | **No** per-identity validation | Anyone with the key is "the caller" |

## The 250-identity limit

> [!NOTE]
> The limit applies to non-Microsoft platforms using app-only client credentials. Foundry and Copilot Studio agents are exempt.

The documented limit of **250 agent identities** applies only to **non-Microsoft platforms that use app-only client credentials**. **Foundry** and **Microsoft Copilot Studio** are exempt. It is not a limit on how many hosted agents you can run in Foundry. Source: [Agent ID FAQ](https://learn.microsoft.com/en-us/entra/agent-id/faq). Note that separate Foundry limits exist (for example 128 tools per agent, per-region session caps; see [doc 06](./06-hosted-agents-explained.md)).

## Five design questions

Settle these before scale. Each card shows the question, the options, and how this demo helps.

### 1. Identity granularity: one identity for all agents, per agent, or per user?

| Option | Pros | Cons |
|---|---|---|
| Shared project identity | Fastest; fewest objects | No separation, cannot revoke one agent; not what a hosted agent runs as in v1.2 |
| **Dedicated instance identity per agent** | Individual authorization and revocation | More objects to govern; must be granted after deploy |
| Per-user delegated (OBO) | Real human accountability | Requires an interactive caller |

**How the demo helps:** it shows both modes (`invoke_as_user.py` for OBO, default scripts for client_credentials) and records which one occurred in the audit.

### 2. Which principal appears in downstream audit?

| Option | Backend audit shows | Trade-off |
|---|---|---|
| Gateway managed identity | The gateway | Simple, loses attribution |
| **Derived `x-gw-*` headers from validated token** | Real agent and human | Needs a trusted gateway and the fragment on every API |
| Runtime key label | Key name only | AI Gateway tier today <img src="./assets/badges/public-preview.svg" alt="Public preview"> |

**How the demo helps:** `human_principal`, `agent_principal`, `gateway` and `caller` fields make the answer visible per call.

### 3. Who owns correlation?

| Option | Pros | Cons |
|---|---|---|
| **DIY with `traceparent` plus KQL join** | Works today, transparent | You maintain it |
| Single vendor trace store only | Easy in one system | Breaks across boundaries (Entra, gateway, tools) |

**How the demo helps:** `traceparent` is created, preserved and parsed everywhere; queries 01, 04 and 11 are the reference joins.

### 4. Lifecycle and governance at thousands of agents

| Option | Pros | Cons |
|---|---|---|
| Foundry control plane + Agent ID governance | Central inventory, lifecycle | Governance features for agents need Agent 365 licensing |
| Tag and policy conventions only | No extra license | Manual, drift-prone |

**How the demo helps:** it applies naming, a dedicated instance identity per agent, and Azure Policy posture (see [doc 10](./10-enterprise-posture-and-scale.md)); licensing is explicit above.

### 5. Runtime coverage for non-Foundry agents

| Option | Pros | Cons |
|---|---|---|
| Require Agent ID tokens everywhere | Uniform attribution | Not all platforms can do it |
| Gateway-issued runtime keys for foreign runtimes | Fast onboarding | Key possession only, no identity |

**How the demo helps:** both gateway lanes run side by side, so you can compare what each proves (table above).

---

Next: [08 - Tools, APIM and MCP topology](./08-tools-apim-mcp-topology.md) →

*Last updated: 2026-10-15*
