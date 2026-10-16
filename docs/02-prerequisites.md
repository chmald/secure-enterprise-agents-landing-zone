[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 02 Prerequisites

# 02 - Prerequisites

<p>
  <img src="./assets/icons/subscription.svg" width="40" alt="Subscription">
  <img src="./assets/icons/entra-roles.svg" width="40" alt="Entra roles">
  <img src="./assets/icons/foundry-models.svg" width="40" alt="Foundry Models">
  <img src="./assets/icons/api-management.svg" width="40" alt="API Management">
  <img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway">
  <img src="./assets/icons/cost-management.svg" width="40" alt="Cost Management">
</p>

<p>
  <img src="./assets/badges/version.svg" alt="pattern: v1.2.0">
  <img src="./assets/badges/public-preview.svg" alt="status: Public preview">
  <img src="./assets/badges/regions-aigw.svg" alt="regions: East US 2 | Sweden Central">
  <img src="./assets/badges/live-tested.svg" alt="validation: Live-tested">
</p>

Prerequisite gate for operators preparing a subscription, tenant, region, and workstation for the v1.2 dual-gateway / dual-agent-framework demo. Work top to bottom; the **pre-flight checklist at the end** is the go/no-go.

## At a glance

| | Gate | Why it matters |
|---|---|---|
| <img src="./assets/icons/subscription.svg" width="24" alt=""> | **Subscription + RBAC** | Role assignments (managed identities, Key Vault, Foundry) need Owner or User Access Administrator. |
| <img src="./assets/icons/app-registrations.svg" width="24" alt=""> | **Entra app rights** | The hook creates a gateway app registration when `GATEWAY_APP_CLIENT_ID` is blank. |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""> | **Preview feature registration** <img src="./assets/badges/public-preview.svg" alt="Public preview"> | The `AIGatewayPreview` feature must be registered, and the AI Gateway tier only exists in East US 2 / Sweden Central during preview. |
| <img src="./assets/icons/foundry-models.svg" width="24" alt=""> | **Model quota** | `gpt-5.5` `2026-04-24` GlobalStandard capacity must exist in your region. |
| <img src="./assets/icons/azure-devops.svg" width="24" alt=""> | **Tooling** | `az`, `azd` + `azure.ai.agents` extension (`>=1.0.0-beta.18`), PowerShell 7, Python 3.11+. |

> [!IMPORTANT]
> Everything dated **2026-10-02** below (regions, models, quotas, previews) is a snapshot. Re-verify at deploy time with the CLI snippets provided.

[![Prerequisites map](./assets/prerequisites-map.png)](./assets/prerequisites-map.png)

<sub>Editable source: [`assets/prerequisites-map.drawio`](./assets/prerequisites-map.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

## Subscription, preview feature registration, and licensing

| | Requirement | Minimum | Notes |
|---|---|---|---|
| <img src="./assets/icons/subscription.svg" width="20" alt=""> | **Azure subscription** | One demo/dev subscription | Must permit APIM, Foundry, Container Apps, Key Vault, Log Analytics, and role assignments. |
| <img src="./assets/icons/entra-roles.svg" width="20" alt=""> | **Subscription RBAC** | Owner, or Contributor + User Access Administrator | Needed for managed identities and Key Vault/Foundry role assignments. |
| <img src="./assets/icons/app-registrations.svg" width="20" alt=""> | **Entra app registration** | Application Administrator, Cloud Application Administrator, or delegated process | Needed for APIM gateway app when `GATEWAY_APP_CLIENT_ID` is blank. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> | **AI Gateway tier preview** <br> <img src="./assets/badges/public-preview.svg" alt="Public preview"> | `AIGatewayPreview` feature registered; East US 2 or Sweden Central | Public preview, no SLA, pricing TBA, and managed in `ai.gateway.azure.com`. Without the feature the deployment fails (see below). |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Foundry hosted agents** <br> <img src="./assets/badges/ga.svg" alt="GA"> | Region/model availability and `azure.ai.agents` azd extension | Both `agent-maf` and `agent-langgraph` deploy with `host: azure.ai.agent`, `kind: hosted`. Sub-features (optimizer, long-running execution, A2A v0.3, routines) are preview. |
| <img src="./assets/icons/entra-id-protection.svg" width="20" alt=""> | **Agent 365 / Conditional Access for agents** | Base Agent ID requires no special license. Conditional Access and Identity Protection on agents need Microsoft Agent 365 (via Microsoft 365 E7, or the Agent 365 add-on plus Entra ID P1 or Microsoft 365 E3). | Do not require a higher Entra tier than current Learn guidance states. This demo does **not** need these features to run. |

### Register the AI Gateway preview feature

> [!WARNING]
> **The AI Gateway tier will not deploy until your subscription has the `AIGatewayPreview` feature registered.** The tier is `Microsoft.ApiManagement/service@2025-09-01-preview` with sku `AIGateway`; without the feature registration (or in an unsupported region) ARM rejects it. The old `Microsoft.ApiManagement/aigateways` type and `2026-05-01-preview` API version never worked in live testing (`InvalidResourceType` / `NoAvailableScaleGroups`) and are not used. Registration is per subscription and can take several minutes.

```powershell
az feature register --namespace Microsoft.ApiManagement --name AIGatewayPreview --subscription <SUBSCRIPTION_ID>
# repeat until the state is "Registered"
az feature show --namespace Microsoft.ApiManagement --name AIGatewayPreview --subscription <SUBSCRIPTION_ID> --query properties.state -o tsv
# propagate the registration to the resource provider
az provider register --namespace Microsoft.ApiManagement --subscription <SUBSCRIPTION_ID>
```

Skip this step only when you deploy with `AI_GATEWAY_MODE=apimv2`.

> [!NOTE]
> The demo itself does not depend on Entra ID P2 or any Agent 365 license. Licensing only matters if you add Conditional Access or Identity Protection for agent identities on top.

## RBAC and identities

> [!IMPORTANT]
> **Console setup requires a human Azure CLI login**, even if the historical infrastructure path could use a pipeline principal. After verifying tenant/subscription, preprovision resolves that user's object ID into `AZURE_PRINCIPAL_ID` and the console allowlist, creates a separate single-tenant Entra app and generates its credential. Directory permission to create/manage apps and credentials is required; Azure subscription RBAC alone is insufficient. Deployment/auth repairs and remaining browser acceptance checks are recorded in the [2026-10-16 follow-up](./04-testing.md#live-follow-up-2026-10-16).

The console backend managed identity additionally needs **Azure AI User** at the Foundry **project**, **Cognitive Services User** at the Foundry **account**, **Log Analytics Reader** at the **workspace**, and **Key Vault Secrets User** at the **vault**. These are distinct from the browser user and agent instance identities. Setup/rotation: [03](./03-deployment.md#demo-console-provisioning-and-sign-in). An isolated console requires a VNet/VPN-connected browser and private DNS, not merely Entra sign-in.

| | Principal | Role | Scope | Why |
|---|---|---|---|---|
| <img src="./assets/icons/entra-roles.svg" width="20" alt=""> | **Deploying user / pipeline** | Owner, or Contributor + User Access Administrator | Subscription (or demo resource group) | Creates resources and role assignments. |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""> | **Deploying user / pipeline** | Key Vault Secrets Officer + Key Vault Secrets User | Demo Key Vault | `postprovision` stores and verifies the AI Gateway runtime key. |
| <img src="./assets/icons/app-registrations.svg" width="20" alt=""> | **Deploying user** | Application Administrator or Cloud Application Administrator | Tenant | Creates the gateway Entra app `gw-<env>` when `GATEWAY_APP_CLIENT_ID` is blank. |
| <img src="./assets/icons/managed-identity.svg" width="20" alt=""> | **Gateway system-assigned managed identity** | **Foundry User** (`53ca6127-db72-4b80-b1b0-d745d6d5456d`) | Foundry account | Gateway calls the model deployment without keys. |
| <img src="./assets/icons/entra-workload-id.svg" width="20" alt=""> | **Hosted-agent instance identity** (one per agent) | **Key Vault Secrets User** (`4633458b-17de-408a-b874-0445c86b69e6`) | Demo Key Vault | Hosted agents read the AI Gateway runtime key. The identity exists only after `azd deploy`, so the `postdeploy` hook grants the role; this is the identity the agent actually runs as (see [07](./07-identity-auth-traceability.md#the-runtime-principal-is-the-instance-identity)). |
| <img src="./assets/icons/managed-identity.svg" width="20" alt=""> | **Foundry project managed identity** | Not used for Key Vault reads | - | Distinct from the instance identity; granting it Key Vault access does not help the running agent. |

Role definitions: [Azure built-in roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles).

## Resource providers

| | Provider | Needed for |
|---|---|---|
| <img src="./assets/icons/api-management.svg" width="20" alt=""> | `Microsoft.ApiManagement` | APIM v2 and the AI Gateway tier (`service` with sku `AIGateway`; needs the `AIGatewayPreview` feature). |
| <img src="./assets/icons/container-apps.svg" width="20" alt=""> | `Microsoft.App` | Container Apps for `catalog-mcp` and `records-api`. |
| <img src="./assets/icons/foundry.svg" width="20" alt=""> | `Microsoft.CognitiveServices` | Foundry account, project, model deployment. |
| <img src="./assets/icons/container-registry.svg" width="20" alt=""> | `Microsoft.ContainerRegistry` | Agent and tool images. |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""> | `Microsoft.KeyVault` | Runtime key storage. |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""> | `Microsoft.OperationalInsights`, `Microsoft.Insights` | Log Analytics, Application Insights, workbooks, alerts. |
| <img src="./assets/icons/virtual-network.svg" width="20" alt=""> | `Microsoft.Network` | Only when `NETWORK_ISOLATION=true`. |

```powershell
foreach ($ns in 'Microsoft.ApiManagement','Microsoft.App','Microsoft.CognitiveServices','Microsoft.ContainerRegistry','Microsoft.KeyVault','Microsoft.OperationalInsights','Microsoft.Insights','Microsoft.ManagedIdentity') {
  az provider register --namespace $ns --subscription <SUBSCRIPTION_ID>
}
az provider show --namespace Microsoft.ApiManagement --subscription <SUBSCRIPTION_ID> --query registrationState -o tsv
```

## Workstation tooling and packages

| | Tool / package | Verify | Purpose |
|---|---|---|---|
| <img src="./assets/icons/azure-devops.svg" width="20" alt=""> | **Azure CLI** | `az version` | Auth, provider registration, manual checks. |
| <img src="./assets/icons/azure-devops.svg" width="20" alt=""> | **Azure Developer CLI** | `azd version` | `azd up`, services, hooks, and outputs. |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **azd extension `azure.ai.agents`** | `azd extension list` | Deploys `agent-maf` and `agent-langgraph`; v1.2 requires `>=1.0.0-beta.18`. |
| <img src="./assets/icons/code.svg" width="20" alt=""> | **PowerShell 7** | `pwsh -Version` | Hooks and profile sync script. |
| <img src="./assets/icons/code.svg" width="20" alt=""> | **Python 3.11+** | `python --version` | Tests and validation scripts. |
| <img src="./assets/icons/container-registry.svg" width="20" alt=""> | **Docker / remote build support** | `docker version` when local builds are used | Hosted-agent and tool images (`remoteBuild: true` avoids local Docker). |
| <img src="./assets/icons/workbooks.svg" width="20" alt=""> | **draw.io Desktop / `DRAWIO_EXE`** | `python scripts/export_diagrams.py docs/assets --check` | Regenerates and verifies PNG diagrams. |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **MAF packages** | `agent-framework-core`, `agent-framework-openai`, `agent-framework-foundry-hosting` (install with `--pre`) | Microsoft Agent Framework hosted agent on the official `ResponsesHostServer`. |
| <img src="./assets/icons/code.svg" width="20" alt=""> | **LangGraph packages** | `langchain-azure-ai[hosting]`, `langchain`, `langchain-openai`, `langchain-mcp-adapters` (install with `--pre`) | LangGraph hosted agent on the official `ResponsesHostServer`. |

Install the azd extension if missing:

```powershell
azd extension install azure.ai.agents
```

## Region tiering and availability

Published snapshot date: **2026-10-02**. Verify at deployment time.

[![Network topology](./assets/network-topology.png)](./assets/network-topology.png)

| | Surface | Region requirement | Recommendation |
|---|---|---|---|
| <img src="./assets/icons/resource-group.svg" width="20" alt=""> | **Primary deployment `AZURE_LOCATION`** | Must support Foundry model, hosted agents, APIM v2, Container Apps, Key Vault, Log Analytics. | `eastus2` is the safest default for this demo. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> | **AI Gateway tier `AI_GATEWAY_TIER_LOCATION`** <img src="./assets/badges/public-preview.svg" alt="Public preview"> | **Only `eastus2` or `swedencentral` during public preview.** | Use `eastus2` unless data residency requires Sweden Central. |
| <img src="./assets/icons/api-management.svg" width="20" alt=""> | **APIM Standard v2 / Premium v2** | Verify SKU in target region. | Standard v2 default; Premium v2 for stricter enterprise networking. |
| <img src="./assets/icons/foundry-models.svg" width="20" alt=""> | **Model deployment** | Verify `MODEL_NAME`, `MODEL_VERSION`, `MODEL_SKU`, and quota. | Keep `gpt-5.5` `2026-04-24` unless explicitly changed. |

### AI Gateway tier region matrix

| Region | AI Gateway tier | Hosted agents | Notes |
|---|---|---|---|
| **East US 2** (`eastus2`) | <img src="./assets/badges/regions-aigw.svg" alt="East US 2 and Sweden Central"> ✅ | ✅ | Recommended default; 2,000 concurrent hosted-agent sessions per region. |
| **Sweden Central** (`swedencentral`) | ✅ | ✅ | Use for EU data-residency conversations; 2,000 concurrent sessions per region. |
| Any other region | ❌ (preview) | ✅ in 31 regions - see list below | `preprovision` rejects other `AI_GATEWAY_TIER_LOCATION` values. |

Legend: ✅ available · ❌ not available · ⚠️ verify.

### Hosted-agent regions

Hosted agents are available in 31 regions as of the Learn snapshot on 2026-10-02; the list is growing. Learn: [Hosted agents concept](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents).

<details>
<summary><b>All 31 hosted-agent regions (2026-10-02)</b></summary>

Australia East · Brazil South · Canada Central · Canada East · Central US · East US · East US 2 · France Central · Germany West Central · Italy North · Japan East · Japan West · Korea Central · North Central US · Norway East · Poland Central · South Africa North · South Central US · South India · Southeast Asia · Spain Central · Sweden Central · Switzerland North · Switzerland West · UAE North · UK South · UK West · West Central US · West Europe · West US · West US 3

</details>

### Preview caveats for AI Gateway tier

| | Caveat | Operational implication |
|---|---|---|
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> | **Public preview; no SLA** <img src="./assets/badges/public-preview.svg" alt="Public preview"> | Use for pilots and validation with rollback to APIM v2. |
| <img src="./assets/icons/cost-management.svg" width="20" alt=""> | **Pricing TBA** | Do not use it for final cost commitments without current pricing. |
| <img src="./assets/icons/policy.svg" width="20" alt=""> | **Management API `2025-09-01-preview`** | Expect API/property churn; validate automation after every update. |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""> | **Runtime access key in `api-key` header** | Store the key in Key Vault; do not treat it as principal identity. If a Key Vault network policy blocks the agent, see [05](./05-troubleshooting.md#hosted-agent-gets-forbiddenbyconnection-from-key-vault). |
| <img src="./assets/icons/entra-id-protection.svg" width="20" alt=""> | **Gateway-scoped keys** | One key reaches all models and tools in the gateway during preview; create separate keys per app/environment where possible. |

> [!WARNING]
> Preview networking (inbound Private Link, outbound VNet integration) for the AI Gateway tier is itself in preview, and the tier private endpoint plus outbound integration are not verified end to end. Do not assume private-only AI Gateway tier traffic in a customer commitment.

## Model availability matrix (dated 2026-10-02)

<img src="./assets/icons/foundry-models.svg" width="20" alt=""> Snapshot from Microsoft Learn research on **2026-10-02**. Capacity differs per subscription and region - always run the verify snippets below before `azd up`.

| Model | Version | SKU | Status in this demo | Retirement | Verdict |
|---|---|---|---|---|---|
| `gpt-5.5` | `2026-04-24` | GlobalStandard | **Default** (`MODEL_NAME`, `MODEL_VERSION`) | 2027-10-26 | ✅ Use |
| `gpt-5.6-sol` / `-luna` / `-terra` | per Learn | GlobalStandard | Alternative; <img src="./assets/badges/ga.svg" alt="GA"> 2026-07-09 | 2028-01-11 | ✅ Optional - change all model vars together |
| `gpt-4o`, `gpt-4.1` | - | - | Avoid - deprecated | 2026-10-14 → 2027-04-14 | ❌ Do not use |
| `gpt-5.1`, `gpt-5.2` | - | - | Avoid - shorter runway | 2027-05-15 / 2027-06-08 | ⚠️ Avoid for new builds |

<details>
<summary><b>Verify model availability and quota (CLI)</b></summary>

```powershell
# Confirm the intended context first - never rely on ambient state
az account show --query "{tenant:tenantId, subscription:id}" -o table

# Is the model/version offered in the region?
az cognitiveservices model list --location eastus2 --subscription <SUBSCRIPTION_ID> `
  --query "[?model.name=='gpt-5.5'].{name:model.name, version:model.version, skus:model.skus[].name}" -o table

# How much GlobalStandard quota is left?
az cognitiveservices usage list --location eastus2 --subscription <SUBSCRIPTION_ID> -o table
```

If `gpt-5.5` is missing or quota is zero, pick another region/model and update `MODEL_NAME`, `MODEL_VERSION`, `MODEL_SKU`, and `MODEL_CAPACITY` together. Learn: [Model retirement schedule](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule).

</details>

## Quotas and limits

| | Limit | Value | Source / note |
|---|---|---|---|
| <img src="./assets/icons/foundry-models.svg" width="20" alt=""> | **Model capacity** | `MODEL_CAPACITY=50` (GlobalStandard capacity units) | Raise or lower to fit your quota. |
| <img src="./assets/icons/policy.svg" width="20" alt=""> | **Per-agent token limit** | `TOKEN_LIMIT_TPM_PER_AGENT=20000` | `llm-token-limit` on APIM. |
| <img src="./assets/icons/policy.svg" width="20" alt=""> | **AI Gateway request limit** | `AIGW_REQUEST_LIMIT_RPM=120` | Request-rate card on the AI Gateway tier. |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Hosted-agent idle timeout** | 2-60 minutes (default 15) | Sessions are deleted after 30 days of inactivity. |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Tools per agent** | 128 | Hosted-agent limit. |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Concurrent sessions per region** | 2,000 in East US 2, Sweden Central, Canada Central, Japan East, North Central US, South Africa North, Southeast Asia; 1,000 elsewhere | Check Learn for the current list. |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Sandbox size** | 0.5 vCPU / 1 GiB (demo default), 1 / 2, 2 / 4 | Set in `azure.yaml`. |
| <img src="./assets/icons/virtual-network.svg" width="20" alt=""> | **Agent subnet (private build)** | `/24` recommended, `/27` hard minimum, delegated to `Microsoft.App/environments` | Demo uses `10.40.0.0/24`. |
| <img src="./assets/icons/container-registry.svg" width="20" alt=""> | **Private ACR** | Foundry projects created after 2026-06-25 | Older projects need a publicly reachable registry. |

## Naming

| | Resource | Pattern (`<env>` = azd environment name, `<sfx>` = 8-char hash) |
|---|---|---|
| <img src="./assets/icons/resource-group.svg" width="20" alt=""> | **azd environment name** | Lowercase alphanumeric + hyphen, starts alphanumeric, no trailing hyphen, **≤ 20 characters** (enforced by `preprovision`). |
| <img src="./assets/icons/foundry.svg" width="20" alt=""> | Foundry account / project | `fdry-<env>-<sfx>` / `proj-<env>` |
| <img src="./assets/icons/api-management.svg" width="20" alt=""> | APIM / AI Gateway tier | `apim-<env>-<sfx>` / `aigw-<env>-<sfx>` |
| <img src="./assets/icons/container-apps-environment.svg" width="20" alt=""> | Container Apps environment | `cae-<env>-<sfx>` |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""> | Key Vault (≤ 24 chars) | `kv-<env>-<sfx>` |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""> | Log Analytics / App Insights | `law-<env>-<sfx>` / `appi-<env>-<sfx>` |

## Cost table (estimate - verify with the Azure Pricing Calculator)

> [!CAUTION]
> These are **relative cost bands, not quotes**. AI Gateway tier pricing is not yet announced. Use the [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) and the Foundry [pricing page](https://azure.microsoft.com/pricing/details/foundry-agent-service/) before committing to a budget.

| | Component | Cost driver | Relative band (estimate) |
|---|---|---|---|
| <img src="./assets/icons/api-management.svg" width="20" alt=""> | **APIM Standard v2** | Fixed per-unit hourly + request volume | 🟧 Highest fixed cost - delete when idle. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> | **AI Gateway tier** <img src="./assets/badges/public-preview.svg" alt="Public preview"> | **Pricing TBA** | ⏳ Unknown. |
| <img src="./assets/icons/foundry-models.svg" width="20" alt=""> | **Foundry model (`gpt-5.5`)** | Tokens in/out | Usage-based; capped by `TOKEN_LIMIT_TPM_PER_AGENT`. |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Hosted-agent runtime** | CPU + memory consumed during **active** sessions | Low for a demo; oversizing multiplies by concurrency. |
| <img src="./assets/icons/container-apps.svg" width="20" alt=""> | **Container Apps (tools)** | vCPU-seconds, memory | Low. |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""> | **Log Analytics / App Insights** | GB ingested × `LOG_RETENTION_DAYS` (90) | Low-medium; `ENABLE_LLM_MESSAGE_LOGGING` increases volume. |
| <img src="./assets/icons/container-registry.svg" width="20" alt=""> <img src="./assets/icons/key-vault.svg" width="20" alt=""> | **ACR, Key Vault** | Tier / operations | Negligible. |
| <img src="./assets/icons/virtual-network.svg" width="20" alt=""> <img src="./assets/icons/private-endpoint.svg" width="20" alt=""> | **Private networking (optional)** | Private endpoints, DNS zones | Adds hourly cost per endpoint. |
| <img src="./assets/icons/sentinel.svg" width="20" alt=""> | **Sentinel (optional)** | GB ingested | Off by default (`ENABLE_SENTINEL=false`). |

## Pre-flight checklist

> [!TIP]
> Run this last, right before `azd up`. Every box should be ticked.

- [ ] Tenant and subscription IDs are known.
- [ ] `az login --tenant <TENANT_ID>` and `azd auth login --tenant-id <TENANT_ID>` completed; `az account show` matches.
- [ ] `AI_GATEWAY_TIER_LOCATION` is `eastus2` or `swedencentral` when the preview tier is enabled.
- [ ] `az feature show --namespace Microsoft.ApiManagement --name AIGatewayPreview` reports `Registered` (tier modes only).
- [ ] `azure.ai.agents` extension is installed (`>=1.0.0-beta.18`).
- [ ] MAF and LangGraph package requirements are understood for local/offline validation.
- [ ] Model/version quota and retirement posture are checked (see the dated matrix).
- [ ] APIM v2 SKU availability checked.
- [ ] Resource providers registered.
- [ ] azd environment name is ≤ 20 characters.
- [ ] Runtime key handling is approved: Key Vault only (or the demo-only `AIGW_KEY_DELIVERY=env` opt-in), never docs/output/logs.
- [ ] Optional diagnostics exports have the required tenant permissions.

Next: [03 - Deployment](./03-deployment.md) →

---

*Last updated: 2026-10-15*
