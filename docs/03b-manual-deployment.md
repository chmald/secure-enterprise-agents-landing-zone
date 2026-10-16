[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 03b Manual deployment

# 03b - Manual Deployment

<p>
  <img src="./assets/icons/resource-group.svg" width="40" alt="Resource group">
  <img src="./assets/icons/log-analytics.svg" width="40" alt="Log Analytics">
  <img src="./assets/icons/foundry.svg" width="40" alt="Foundry">
  <img src="./assets/icons/api-management.svg" width="40" alt="API Management">
  <img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway">
  <img src="./assets/icons/container-apps.svg" width="40" alt="Container Apps">
</p>

<p>
  <img src="./assets/badges/diy.svg" alt="path: manual / DIY">
  <img src="./assets/badges/public-preview.svg" alt="AI Gateway tier: public preview">
  <img src="./assets/badges/regions-aigw.svg" alt="regions: East US 2 and Sweden Central">
  <img src="./assets/badges/static-only.svg" alt="validation: manual path not live-run">
</p>

Manual provisioning path for workshops or constrained environments where `azd up` is not allowed. It creates the same resource classes as the IaC path, but the AI Gateway tier preview is currently portal-first for many operators, so expect extra validation time. The v1.2 live run used `azd up`; this manual path is **not** live-validated.

> [!IMPORTANT]
> **Scope: historical core resources, not a complete manual console deployment.** The new browser console uses the supported [azd provisioning path](./03-deployment.md#demo-console-provisioning-and-sign-in), including human-deployer resolution, separate single-tenant Entra app/credential setup, redirect registration, Easy Auth allowlist and managed-identity grants. This portal guide does not reproduce those hooks. Do not claim manual-path console parity; the [limited console live checks](./04-testing.md#live-follow-up-2026-10-16) used the azd-deployed application.

## At a glance

| | | |
|---|---|---|
| <img src="./assets/icons/azure-devops.svg" width="24" alt=""> | **Use when** | `azd` is blocked, or the workshop wants each resource created visibly in the portal |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""> | **Highlight** | Portal walkthrough of the AI Gateway tier at `ai.gateway.azure.com` |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""> | **Agents** | Still best deployed with `azd deploy agent-maf agent-langgraph` |
| <img src="./assets/icons/cost-management.svg" width="24" alt=""> | **Trade-off** | Slower and more drift-prone than `azd up` - see the [time delta](#time-delta-manual-vs-azd) |

> [!NOTE]
> Complete [02 - Prerequisites](./02-prerequisites.md) first - the same RBAC, region, model, and quota gates apply, including the `AIGatewayPreview` feature registration for the AI Gateway tier.

[![Manual deployment steps](./assets/manual-deployment-steps.png)](./assets/manual-deployment-steps.png)

<sub>Editable source: [`assets/manual-deployment-steps.drawio`](./assets/manual-deployment-steps.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

## When to use this path

| Use manual path when | Prefer `azd up` when |
|---|---|
| A workshop wants participants to see each resource created in the portal. | You need repeatability, teardown, and lower drift risk. |
| Policy blocks azd but permits portal/imperative CLI. | You can run Bicep through azd. |
| You need to demonstrate AI Gateway tier portal steps. | You are building an environment for reuse. |

## Tenant-explicit context

> [!WARNING]
> Set the tenant and subscription explicitly before creating anything. Ambient `az` state can point at a different tenant.

```powershell
az login --tenant <TENANT_ID>
az account set --subscription <SUBSCRIPTION_ID>
az account show --query "{tenant:tenantId, subscription:id, subName:name, user:user.name}" -o table
```

## Manual provisioning map

| | Phase | Manual action | Notes |
|---|---|---|---|
| <img src="./assets/icons/resource-group.svg" width="20" alt=""> | **Resource group / providers** | Create the resource group and register providers. | Include `Microsoft.ApiManagement`, `Microsoft.App`, `Microsoft.CognitiveServices`, `Microsoft.KeyVault`, `Microsoft.OperationalInsights`, `Microsoft.Insights`. |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""> | **Monitoring** | Create Log Analytics, workspace-based Application Insights, query pack, workbook. | Import query files including `11-ai-gateway-tier-telemetry.kql`. |
| <img src="./assets/icons/foundry.svg" width="20" alt=""> | **Foundry** | Create account, project, and model deployment. | Keep `MODEL_DEPLOYMENT_NAME=chat` unless changed everywhere. |
| <img src="./assets/icons/api-management.svg" width="20" alt=""> | **APIM v2** | Create Standard v2 / Premium v2 APIM, APIs, policies, diagnostics. | Import `infra/policies/*`; validate the Entra audience. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> | **AI Gateway tier** | `https://ai.gateway.azure.com` → Create gateway → supported region → import Foundry model → add MCP/OpenAPI tool servers → create runtime key. | East US 2 or Sweden Central; store the runtime key in Key Vault as `aigw-runtime-key`. |
| <img src="./assets/icons/container-apps.svg" width="20" alt=""> | **Container Apps** | Deploy `catalog-mcp` and `records-api`. | Use port 8080 for backends. |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Hosted agents** | Prefer `azd deploy agent-maf agent-langgraph` even if infra was manual. | If fully manual, use the hosted-agent manifests under `src/agents/maf` and `src/agents/langgraph`; grant the instance identity Key Vault access yourself (the `postdeploy` hook only runs under azd). |
| <img src="./assets/icons/code.svg" width="20" alt=""> | **Profiles** | Run `scripts/sync-agent-profiles.ps1` before container builds when root profile JSON changes. | Each hosted-agent Docker context contains a copied `profiles/` folder. |

## Portal walkthrough per resource

Each card names the portal blade and the value to enter. Resource naming guidance is in [02](./02-prerequisites.md#naming).

### <img src="./assets/icons/resource-group.svg" width="28" alt=""> Step 1 - Resource group and providers

| Step | Action | Checkpoint |
|---|---|---|
| 1.1 | Portal › **Resource groups** › **Create**; pick the subscription, name, and region (`eastus2` recommended). | - [ ] Group exists |
| 1.2 | Portal › **Subscriptions** › your subscription › **Resource providers**; register the six providers above. | - [ ] All show *Registered* |

### <img src="./assets/icons/log-analytics.svg" width="28" alt=""> Step 2 - Monitoring plane

| Step | Action | Checkpoint |
|---|---|---|
| 2.1 | **Log Analytics workspace** › Create; retention 90 days. | - [ ] Workspace ready |
| 2.2 | <img src="./assets/icons/application-insights.svg" width="18" alt=""> **Application Insights** › Create, *workspace-based*, linked to the workspace. | - [ ] Connection string available (do not paste it into docs) |
| 2.3 | <img src="./assets/icons/query-pack.svg" width="18" alt=""> / <img src="./assets/icons/workbooks.svg" width="18" alt=""> Import the `.kql` files as a query pack and the workbook from the repo. | - [ ] Query `11` present |

### <img src="./assets/icons/foundry.svg" width="28" alt=""> Step 3 - Microsoft Foundry

| Step | Action | Checkpoint |
|---|---|---|
| 3.1 | <img src="./assets/icons/foundry.svg" width="18" alt=""> **Microsoft Foundry** › Create account and project. | - [ ] Project created |
| 3.2 | <img src="./assets/icons/foundry-models.svg" width="18" alt=""> **Models + endpoints** › Deploy `gpt-5.5` `2026-04-24`, GlobalStandard, deployment name `chat`. | - [ ] Deployment *Succeeded* |
| 3.3 | Connect the shared Application Insights to the project. | - [ ] Tracing enabled |

### <img src="./assets/icons/key-vault.svg" width="28" alt=""> Step 4 - Key Vault and identities

| Step | Action | Checkpoint |
|---|---|---|
| 4.1 | <img src="./assets/icons/key-vault.svg" width="18" alt=""> **Key Vault** › Create with Azure RBAC authorization. | - [ ] Vault exists |
| 4.2 | <img src="./assets/icons/managed-identity.svg" width="18" alt=""> After the agents are deployed, grant each hosted agent's **instance identity** (`azd ai agent show <agent> --output json` → `instance_identity.principal_id`) **Key Vault Secrets User**. The Foundry project identity is not the runtime identity. | - [ ] Assignment visible for both agents |
| 4.3 | <img src="./assets/icons/app-registrations.svg" width="18" alt=""> **Entra ID › App registrations** › create the gateway app (needed for APIM v2 token validation). | - [ ] App (client) ID recorded |

### <img src="./assets/icons/api-management.svg" width="28" alt=""> Step 5 - API Management v2

| Step | Action | Checkpoint |
|---|---|---|
| 5.1 | **API Management** › Create **Standard v2** (or Premium v2). | - [ ] Instance active |
| 5.2 | Enable the system-assigned identity and grant it **Foundry User** on the Foundry account. | - [ ] Assignment visible |
| 5.3 | Create the LLM API (`/llm`), `catalog-mcp`, `records-mcp`, and `records` APIs; paste in `infra/policies/*`. | - [ ] Policies saved |
| 5.4 | Validate the Entra audience: gateway app audience **and** `https://cognitiveservices.azure.com`. | - [ ] Token test passes |
| 5.5 | Add diagnostics to Log Analytics (resource-specific). | - [ ] Logs appear after a test call |

### <img src="./assets/icons/container-apps.svg" width="28" alt=""> Step 6 - Container Registry and Container Apps

| Step | Action | Checkpoint |
|---|---|---|
| 6.1 | <img src="./assets/icons/container-registry.svg" width="18" alt=""> **Container Registry** › Create; build the `catalog-mcp` and `records-api` images (ACR Tasks). | - [ ] Images pushed |
| 6.2 | <img src="./assets/icons/container-apps-environment.svg" width="18" alt=""> **Container Apps environment** › Create, wired to Log Analytics. | - [ ] Environment ready |
| 6.3 | <img src="./assets/icons/container-apps.svg" width="18" alt=""> Create two container apps on port **8080**, set `DOMAIN_PROFILE`. | - [ ] `/health` responds |

### <img src="./assets/icons/foundry-agent-service.svg" width="28" alt=""> Step 7 - Hosted agents

| Step | Action | Checkpoint |
|---|---|---|
| 7.1 | Preferred: `azd env set` the values in [03](./03-deployment.md#phase-1---configure-deployment-knobs), then `azd deploy agent-maf agent-langgraph`. | - [ ] Both agents listed in the Foundry portal |
| 7.2 | Fully manual: publish from the manifests in `src/agents/maf` and `src/agents/langgraph`. | - [ ] Agent versions created |
| 7.3 | If root profile JSON changed, run `scripts/sync-agent-profiles.ps1` first. | - [ ] `profiles/` copies updated |

## Portal steps for the AI Gateway tier

<img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway">

> [!IMPORTANT]
> The AI Gateway tier is **public preview** (no SLA, pricing TBA). Register the `AIGatewayPreview` feature first ([02](./02-prerequisites.md#register-the-ai-gateway-preview-feature)). Portal labels may change; follow the intent of each step. The model alias name must equal the `model` your agents send (`chat`), and the provider model name must equal the Foundry deployment name.

| Step | | Action | Checkpoint |
|---|---|---|---|
| **1** | <img src="./assets/icons/entra-id.svg" width="24" alt=""> | Open `https://ai.gateway.azure.com` and sign in with Microsoft Entra ID. | - [ ] Signed in to the right tenant |
| **2** | <img src="./assets/icons/ai-gateway.svg" width="24" alt=""> | Select **Create gateway**; choose subscription and resource group; select `East US 2` or `Sweden Central`. | - [ ] Gateway created |
| **3** | <img src="./assets/icons/foundry-models.svg" width="24" alt=""> | Import model deployments from Microsoft Foundry using managed identity; ensure the gateway identity has the **Foundry User** role (`53ca6127-db72-4b80-b1b0-d745d6d5456d`). | - [ ] Model listed under `/default/models/openai/v1` |
| **4** | <img src="./assets/icons/toolbox.svg" width="24" alt=""> | Add MCP servers: one remote MCP backend for `catalog-mcp`, one OpenAPI-generated tool server for `records-api`. | - [ ] Two tool servers listed |
| **5** | <img src="./assets/icons/key-vault.svg" width="24" alt=""> | Create runtime access key `agents`; copy it **once** and store it in Key Vault secret `aigw-runtime-key`. | - [ ] Secret present; value not recorded anywhere else |
| **6** | <img src="./assets/icons/content-safety.svg" width="24" alt=""> | Add policy cards for content safety, request rate limit, and token rate limit (an IP filter card also exists). | - [ ] Cards saved |
| **7** | <img src="./assets/icons/application-insights.svg" width="24" alt=""> | Connect the shared Application Insights resource so the tier's request telemetry lands in `AppRequests`. | - [ ] Query `11` returns rows after traffic |

> [!WARNING]
> The runtime key is gateway-scoped: one key reaches every model and tool on the gateway. Create separate keys per app or environment, and never paste the value into docs, tickets, or logs.

Learn: [AI gateway in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/genai-gateway-capabilities) · [Enable AI Gateway in the Foundry portal](https://learn.microsoft.com/en-us/azure/foundry/configuration/enable-ai-api-management-gateway-portal) (the APIM-based Foundry portal feature, a different path from `ai.gateway.azure.com`).

## Hand-populate local IDs

<img src="./assets/icons/diagnostic-settings.svg" width="20" alt=""> Copy `demo-ids.template.json` to `demo-ids.local.json` and fill in APIM, AI Gateway tier, Key Vault, workspace, and Foundry keys. Never add runtime key values or connection strings.

## Time delta: manual vs azd

> [!NOTE]
> Figures are rough planning estimates, not measurements - your tenant, region, and familiarity will shift them.

| | Activity | `azd up` | Manual (portal) |
|---|---|---|---|
| <img src="./assets/icons/azure-devops.svg" width="20" alt=""> | Environment setup + auth | Minutes | Minutes |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""> | Monitoring plane + query pack | Automatic | Manual import per query/workbook |
| <img src="./assets/icons/api-management.svg" width="20" alt=""> | APIM v2 + policies | Automatic (APIM v2 provisioning dominates wall-clock time) | Longer - policy and API paste per API |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> | AI Gateway tier | Bicep + runtime-key hook (about 3 minutes to provision) | Portal-first; extra validation time |
| <img src="./assets/icons/container-apps.svg" width="20" alt=""> | Container Apps + images | Automatic (`remoteBuild`) | Build and deploy each app |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> | Hosted agents | `azd deploy agent-maf agent-langgraph` | Same command recommended |
| <img src="./assets/icons/resource-group.svg" width="20" alt=""> | Teardown | `azd down --purge --force` (about 36 minutes live) | Delete resources and purge soft-deleted names by hand |
| | **Overall** | **Fastest, repeatable** | **Several times longer; drift-prone** |

## Continue with testing

```powershell
python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2
python scripts/validate_gateway.py --ids demo-ids.local.json --target aigateway
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway aigateway --dry-run
```

---

Next: [04 - Testing](./04-testing.md) →

*Last updated: 2026-10-15*
