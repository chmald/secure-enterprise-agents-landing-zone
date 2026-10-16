[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 00 Reproduce this demo

# 00 - Reproduce This Demo

<p>
  <img src="./assets/icons/subscription.svg" width="40" alt="Subscription">
  <img src="./assets/icons/entra-id.svg" width="40" alt="Microsoft Entra ID">
  <img src="./assets/icons/api-management.svg" width="40" alt="API Management">
  <img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway">
  <img src="./assets/icons/foundry-agent-service.svg" width="40" alt="Foundry Agent Service">
  <img src="./assets/icons/log-analytics.svg" width="40" alt="Log Analytics">
</p>

<p>
  <img src="./assets/badges/version.svg" alt="pattern: v1.2.0">
  <img src="./assets/badges/default.svg" alt="mode: Default">
  <img src="./assets/badges/public-preview.svg" alt="status: Public preview">
  <img src="./assets/badges/live-tested.svg" alt="validation: Live-tested">
  <img src="./assets/badges/static-only.svg" alt="validation: Network isolation static-only">
</p>

Single-page orchestrator for standing up the **Foundry Hosted Agents + AI Gateway Landing Zone** from an empty Azure subscription. Use it for checkpoints before opening the deeper runbooks. It is written for the person who will actually run the build - typically a platform engineer or developer - and every part ends with a checkpoint you can tick off.

> [!IMPORTANT]
> **Browser path: deployed with limited live checks, not a completed browser acceptance matrix.** See the [2026-10-16 follow-up](./04-testing.md#live-follow-up-2026-10-16). One-time provisioning still uses the CLI; presenting S1-S5 does not. `azd up` includes `demo-console` (remote build, repository-root Docker context). For an existing environment run `azd provision`, then `azd deploy records-api demo-console` so the REST collection-routing fix ships too. Open `DEMO_CONSOLE_URL` as the deploying human. Earlier badges/evidence describe the script-driven deployment only.

### Browser reproduction checkpoints

1. Complete Part A with a human Azure CLI login in the intended tenant/subscription. Before setup operations, `preprovision` verifies that context, resolves `AZURE_PRINCIPAL_ID` from the signed-in user, and ensures a separate single-tenant console Entra app and credential. App/credential creation permissions are required.
2. Provision with the existing hooks ([03 - Console setup](./03-deployment.md#demo-console-provisioning-and-sign-in)). `DEMO_CONSOLE_CLIENT_ID`, `DEMO_CONSOLE_ALLOWED_USER_ID`, and `DEMO_CONSOLE_CLIENT_SECRET` must be populated by setup before deployment; blank defaults fail closed. Do not print or commit secret-bearing azd state.
3. Check outputs `DEMO_CONSOLE_URL` and `DEMO_CONSOLE_APP_NAME`; sign in as the deployer. Easy Auth is tenant-only and deployer-allowlisted; the backend verifies the platform-injected principal ID and rejects conflicting owner/tenant claims when supplied. With `NETWORK_ISOLATION=true`, the console is in the internal ACA environment: use a VNet/VPN-connected browser and working private DNS.
4. Follow [browser S1-S5](./11-demo-walkthrough.md#browser-console-s1-s5). Confirm **every** agent submission (tools can mutate), direct write and bounded throttle burst separately. Inspect raw details and statuses; no 429/empty logs means `not_run`, not success.
5. Keep agent routing separate from direct checks: the dropdown does not change deployed `HOSTED_DEFAULT_GATEWAY`. The displayed hosted gateway is a **provisioning snapshot**, not live discovery; after changing `AGENT_DEFAULT_GATEWAY`, run `azd provision` to sync console configuration as well as redeploying agents. OBO, optional ACA agent comparison, and network isolation verification remain manual/unavailable unless explicitly deployed/verified. The console never runs CLI commands or scripts inside the app.

## At a glance

| | Item | Value |
|---|---|---|
| <img src="./assets/icons/subscription.svg" width="24" alt=""> | **Starting point** | Empty subscription + tenant where you can register an Entra app. |
| <img src="./assets/icons/azure-devops.svg" width="24" alt=""> | **Tooling** | Azure CLI, Azure Developer CLI (`azd`) + `azure.ai.agents` extension, PowerShell 7, Python 3.11+. |
| <img src="./assets/icons/api-management.svg" width="24" alt=""> | **Default path** | `AI_GATEWAY_MODE=both` for validation; `AGENT_DEFAULT_GATEWAY=apimv2` first (the agents receive it as `HOSTED_DEFAULT_GATEWAY`). |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""> | **End state** | Two hosted agents + two tool backends behind configured gateways, plus a deployer-only browser console; audit rows must be verified after ingestion. |
| <img src="./assets/icons/cost-management.svg" width="24" alt=""> | **Time** | 4-6 hours first build; 90-150 minutes repeat build. |

> [!IMPORTANT]
> Do the checks in [02 - Prerequisites](./02-prerequisites.md) first - model quota, the `AIGatewayPreview` feature registration, and tenant permissions are the three things that turn a 2-hour build into a 2-day build.

## Time budget

| | Build type | Hands-on time | Elapsed time | Notes |
|---|---|---:|---:|---|
| <img src="./assets/icons/azure-devops.svg" width="20" alt=""> | **First build** | 4-6 hours | 1 business day | Includes provider and `AIGatewayPreview` feature registration, model quota checks, first `azd up`, hosted-agent deployment, and propagation delays. |
| <img src="./assets/icons/azure-devops.svg" width="20" alt=""> | **Subsequent build** | 90-150 minutes | 2-3 hours | Assumes quota, providers, feature registration, and tenant permissions are already settled. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> | **`AI_GATEWAY_MODE=both`** <img src="./assets/badges/public-preview.svg" alt="Public preview"> | +30-60 minutes | +1-2 hours | Adds AI Gateway tier validation (about 3 minutes to provision) and second-pass hosted-agent deployment. |
| <img src="./assets/icons/private-link.svg" width="20" alt=""> | **Private-network build** | +1-2 hours | +1 day if DNS/firewall approval is needed | Adds private endpoints, DNS validation, and network troubleshooting. <img src="./assets/badges/static-only.svg" alt="Static only"> |

## End state

[![Architecture](./assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.png)](./assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.png)

<sub>Editable source: [`assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.drawio`](./assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

```text
Browser (tenant-only Entra Easy Auth + backend deployer principal-ID validation)
   │
   ▼
ca-demo-console (existing ACA environment; managed identity)
   ├──────────────► Direct gateway checks + bounded saved KQL (01-11)
   │
   ▼
Foundry hosted agents:  agent-maf   agent-langgraph      (official hosts, responses 2.0.0, port 8088)
   │  (HOSTED_DEFAULT_GATEWAY = apimv2 | aigateway)
   ├──────────────► APIM Standard v2  ──► Foundry model (gpt-5.5)   [Entra token, llm-* policies]
   │                     └────────────► catalog-mcp / records-api   [MCP allow-list, audit headers]
   └──────────────► AI Gateway tier    ──► Foundry model + tool servers   [api-key]
                          │
Key Vault (runtime key) ──┘        Application Insights + Log Analytics + workbook + KQL
```

The console is not an OBO client. Direct APIM checks identify its managed identity; the AI Gateway tier checks a runtime key. Existing scripts and the OBO sample remain separate developer/manual paths below.

## Parts A-F

| Part | | Goal | Doc for depth |
|---|---|---|---|
| **A** | <img src="./assets/icons/entra-id.svg" width="24" alt=""> | Ground truth and authentication | [03 Phase 0](./03-deployment.md) |
| **B** | <img src="./assets/icons/diagnostic-settings.svg" width="24" alt=""> | Configure both gateway paths | [12 Configuration reference](./12-configuration-reference.md) |
| **C** | <img src="./assets/icons/container-apps.svg" width="24" alt=""> | Preview (what-if) and deploy <img src="./assets/badges/live-tested.svg" alt="Live-tested"> | [03 Deployment](./03-deployment.md) |
| **D** | <img src="./assets/icons/api-management.svg" width="24" alt=""> | Validate both gateways | [04 Testing](./04-testing.md) |
| **E** | <img src="./assets/icons/ai-gateway.svg" width="24" alt=""> | Switch hosted agents to the AI Gateway tier <img src="./assets/badges/public-preview.svg" alt="Public preview"> | [03 Deployment](./03-deployment.md) |
| **F** | <img src="./assets/icons/log-analytics.svg" width="24" alt=""> | Audit proof and regression | [09 Monitoring and audit](./09-monitoring-and-audit.md) |

### Part A - Ground truth and authentication <img src="./assets/icons/entra-id.svg" width="24" alt="">

> [!WARNING]
> `az` and `azd` keep **separate** logins, and the ambient active account silently drifts across tenants. Always sign in with an explicit tenant and verify before any deployment. Never deploy a demo into a production or shared corporate tenant by accident.

| Step | | Action | Validation |
|---|---|---|---|
| **A1** | <img src="./assets/icons/entra-id.svg" width="24" alt="Entra ID"> | `azd auth login --tenant-id <TENANT_ID>` and `az login --tenant <TENANT_ID>`. | - [ ] Both sign-ins succeed for the same tenant. |
| **A2** | <img src="./assets/icons/subscription.svg" width="24" alt="Subscription"> | `az account set --subscription <SUBSCRIPTION_ID>`; verify with `az account show`. | - [ ] Tenant + subscription match the intended target. |
| **A3** | <img src="./assets/icons/resource-group.svg" width="24" alt="Resource group"> | `azd env new` and set `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_LOCATION`. | - [ ] `azd env get-values` shows all three. |

<details>
<summary><b>Part A commands</b></summary>

```powershell
$tenant = "<TENANT_ID>"
$subscription = "<SUBSCRIPTION_ID>"
$location = "eastus2"
$envName = "<ENV_NAME>"

azd auth login --tenant-id $tenant
az login --tenant $tenant
az account set --subscription $subscription
az account show --query "{tenant:tenantId, subscription:id, subName:name, user:user.name}" -o table

azd env new $envName
azd env set AZURE_TENANT_ID $tenant
azd env set AZURE_SUBSCRIPTION_ID $subscription
azd env set AZURE_LOCATION $location
```

</details>

### Part B - Configure both gateway paths <img src="./assets/icons/diagnostic-settings.svg" width="24" alt="">

| Step | | Action | Validation |
|---|---|---|---|
| **B1** | <img src="./assets/icons/ai-gateway.svg" width="24" alt="AI Gateway"> | Set `AI_GATEWAY_MODE both`, `AI_GATEWAY_TIER_LOCATION eastus2`, `AIGW_REQUEST_LIMIT_RPM`, `AIGW_RUNTIME_KEY_SECRET_NAME`. <img src="./assets/badges/public-preview.svg" alt="Public preview"> | - [ ] Tier location is `eastus2` or `swedencentral`; the `AIGatewayPreview` feature is `Registered` ([02](./02-prerequisites.md#register-the-ai-gateway-preview-feature)). |
| **B2** | <img src="./assets/icons/api-management.svg" width="24" alt="API Management"> | Set `AGENT_DEFAULT_GATEWAY apimv2`, `APIM_SKU StandardV2`, `APIM_PUBLISHER_EMAIL`. | - [ ] Publisher email is a mailbox you control. |
| **B3** | <img src="./assets/icons/foundry-models.svg" width="24" alt="Foundry Models"> | Set the model (`gpt-5.5` `2026-04-24` `GlobalStandard`, capacity 50, deployment `chat`). | - [ ] Quota verified per [02](./02-prerequisites.md#model-availability-matrix-dated-2026-10-02). |
| **B4** | <img src="./assets/icons/content-safety.svg" width="24" alt="Content Safety"> | Set `DOMAIN_PROFILE`, `ENABLE_LLM_MESSAGE_LOGGING`, `ENABLE_CONTENT_SAFETY`, `ENABLE_ALERTS`. | - [ ] Profile file exists under `config/profiles/`. |

<details>
<summary><b>Part B commands</b></summary>

```powershell
azd env set AI_GATEWAY_MODE both
azd env set AI_GATEWAY_TIER_LOCATION eastus2
azd env set AIGW_REQUEST_LIMIT_RPM 120
azd env set AIGW_RUNTIME_KEY_SECRET_NAME aigw-runtime-key
azd env set AGENT_DEFAULT_GATEWAY apimv2
azd env set APIM_SKU StandardV2
azd env set APIM_PUBLISHER_EMAIL <you@example.com>
azd env set MODEL_NAME gpt-5.5
azd env set MODEL_VERSION 2026-04-24
azd env set MODEL_DEPLOYMENT_NAME chat
azd env set MODEL_SKU GlobalStandard
azd env set MODEL_CAPACITY 50
azd env set DOMAIN_PROFILE manufacturing-field-ops
azd env set ENABLE_LLM_MESSAGE_LOGGING true
azd env set ENABLE_CONTENT_SAFETY true
azd env set ENABLE_ALERTS true
```

</details>

### Part C - Preview and deploy <img src="./assets/icons/container-apps.svg" width="24" alt="">

| Step | | Action | Validation |
|---|---|---|---|
| **C1** | <img src="./assets/icons/resource-group.svg" width="24" alt="Resource group"> | `azd provision --preview` to review the what-if. | - [ ] No unexpected deletes; AI Gateway tier resources (`Microsoft.ApiManagement/service`, sku `AIGateway`) listed when mode is `aigateway`/`both`. |
| **C2** | <img src="./assets/icons/azure-devops.svg" width="24" alt="azd"> | <img src="./assets/badges/live-tested.svg" alt="Live tested"> `azd up` provisions infra, runs hooks, deploys tools and agents; each agent's `postdeploy` hook grants its instance identity Key Vault Secrets User. | - [ ] `demo-ids.local.json` written by `postprovision`; the `postdeploy` summary shows `granted` or `exists`. |
| **C3** | <img src="./assets/icons/key-vault.svg" width="24" alt="Key Vault"> | Hook stores the `agents` runtime key in Key Vault as `AIGW_RUNTIME_KEY_SECRET_NAME`. | - [ ] Secret exists (do not print it). Under a Key Vault network policy see [05](./05-troubleshooting.md#hosted-agent-gets-forbiddenbyconnection-from-key-vault). |

```powershell
azd provision --preview
azd up
```

`postprovision` writes `demo-ids.local.json` and stores the AI Gateway runtime key `agents` in Key Vault as `AIGW_RUNTIME_KEY_SECRET_NAME` (or, with `AIGW_KEY_DELIVERY=env`, in the azd environment - a demo-only compromise, see [03](./03-deployment.md#key-delivery-and-the-postdeploy-hook)). Prerequisite: the `AIGatewayPreview` feature must be registered before `azd provision`.

### Part D - Validate both gateways <img src="./assets/icons/api-management.svg" width="24" alt="">

| Step | | Action | Validation |
|---|---|---|---|
| **D1** | <img src="./assets/icons/api-management.svg" width="24" alt="API Management"> | Validate the default gateway (`--target apimv2`). | - [ ] Model, MCP, and REST routes answer; missing token is rejected. |
| **D2** | <img src="./assets/icons/ai-gateway.svg" width="24" alt="AI Gateway"> | Validate the AI Gateway tier (`--target aigateway`, model alias `chat`). | - [ ] `api-key` accepted; missing key rejected. |

```powershell
python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2
python scripts/validate_gateway.py --ids demo-ids.local.json --target aigateway
```

### Part E - Switch hosted agents to the AI Gateway tier <img src="./assets/icons/ai-gateway.svg" width="24" alt="">

| Step | | Action | Validation |
|---|---|---|---|
| **E1** | <img src="./assets/icons/foundry-agent-service.svg" width="24" alt="Foundry Agent Service"> | Set `AGENT_DEFAULT_GATEWAY aigateway`; redeploy only the agents. | - [ ] `azd deploy agent-maf agent-langgraph` completes. |
| **E2** | <img src="./assets/icons/workbooks.svg" width="24" alt="Workbooks"> | Dry-run the walkthrough against the AI Gateway tier. | - [ ] Every step resolves to the expected tool. |

```powershell
azd env set AGENT_DEFAULT_GATEWAY aigateway
azd deploy agent-maf agent-langgraph
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway aigateway --dry-run
```

> [!NOTE]
> The v1.2 live run passed S1-S5 for both agents on both gateways; see [04 - Testing](./04-testing.md#live-validation-2026-10-02) for timings and the defects found.

### Part F - Audit proof and regression <img src="./assets/icons/log-analytics.svg" width="24" alt="">

| Step | | Action | Validation |
|---|---|---|---|
| **F1** | <img src="./assets/icons/log-analytics.svg" width="24" alt="Log Analytics"> | Query 01 (who called which tool) and query 11 (AI Gateway tier telemetry). | - [ ] Query 01 shows tool rows; query 11 has rows after traffic. |
| **F2** | <img src="./assets/icons/query-pack.svg" width="24" alt="Query pack"> | Check diagram freshness and run the test suite. | - [ ] `pytest` passes; `export_diagrams.py --check` is clean. |

```powershell
python scripts/run_audit_queries.py --ids demo-ids.local.json --query 01
python scripts/run_audit_queries.py --ids demo-ids.local.json --query 11
python scripts/export_diagrams.py docs/assets --check
pytest
```

> [!TIP]
> On `apimv2`, query 01 rows carry `agent_principal` / `human_principal` derived from Entra tokens. On `aigateway`, the audit row honestly shows `gateway="aigateway"`, `caller="aigw-runtime-key:agents"`, `agent_principal=null`. That difference is the point of the comparison - see [01 - Architecture](./01-architecture.md#trust-boundaries).

## If you get stuck

Start with the decision tree in [05-troubleshooting.md](./05-troubleshooting.md), especially tenant drift, the `AIGatewayPreview` feature registration, runtime-key 401s, model-alias 404s, and Key Vault `ForbiddenByConnection` errors.

> [!TIP]
> Most v1.2 failures fall into four buckets: tenant/subscription drift, a missing feature registration, a model name that does not match the alias, and the agent identity lacking Key Vault access.

Next: [01 - Architecture](./01-architecture.md) →

---

*Last updated: 2026-10-15*
