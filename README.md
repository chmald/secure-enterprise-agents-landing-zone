# Secure Enterprise Agents Landing Zone

> Formerly published as `foundry-hosted-agents-ai-gateway-landing-zone`. Old links redirect automatically.

**Run enterprise AI agents securely:** Foundry hosted agents behind an AI Gateway, with governed model and tool access and audit-first landing-zone posture.

**Present from a browser:** the Azure-hosted [demo console](./docs/11-demo-walkthrough.md#browser-console-s1-s5) runs the S1-S5 story without local demo scripts after provisioning. It uses FastAPI and plain HTML/CSS/JS in one Container App, `ca-demo-console`, in the existing environment. Sign in as the deploying human; other users are denied.

> [!IMPORTANT]
> **The console is deployed with limited live checks; the complete browser acceptance matrix remains pending.** See the [2026-10-16 follow-up](./docs/04-testing.md#live-follow-up-2026-10-16) for the auth/key-delivery repairs, verified paths and remaining gaps. Historical 2026-10-02 badges/evidence below cover the earlier script-driven deployment. Confirmations gate all agent prompts (agents can mutate data), direct writes, and throttle bursts. Use disposable sample data only.

<p align="center">
  <img src="./docs/assets/icons/foundry.svg" width="40" alt="Microsoft Foundry">
  <img src="./docs/assets/icons/foundry-agent-service.svg" width="40" alt="Foundry Agent Service">
  <img src="./docs/assets/icons/api-management.svg" width="40" alt="API Management">
  <img src="./docs/assets/icons/ai-gateway.svg" width="40" alt="AI Gateway">
  <img src="./docs/assets/icons/container-apps.svg" width="40" alt="Container Apps">
  <img src="./docs/assets/icons/key-vault.svg" width="40" alt="Key Vault">
  <img src="./docs/assets/icons/entra-id.svg" width="40" alt="Microsoft Entra ID">
  <img src="./docs/assets/icons/application-insights.svg" width="40" alt="Application Insights">
</p>

<p align="center">
  <img src="./docs/assets/badges/version.svg"   alt="pattern: v1.2.0">
  <img src="./docs/assets/badges/default.svg" alt="mode: Default">
  <img src="./docs/assets/badges/public-preview.svg" alt="status: Public preview">
  <img src="./docs/assets/badges/protocol.svg" alt="protocol: responses 2.0.0">
  <img src="./docs/assets/badges/regions-aigw.svg" alt="regions: East US 2 | Sweden Central">
    <img src="./docs/assets/badges/live-tested.svg" alt="validation: Live-tested (both gateways, both agents)">
    <img src="./docs/assets/badges/static-only.svg" alt="validation: Network isolation static-only">
  </p>

> [!WARNING]
> **For testing and demonstration purposes only.** This is a personal reference demo provided "as is" under the [MIT License](LICENSE), without warranty or support. It is not an official Microsoft product or sample, has not been through a production security review, and is not intended for production use. Review, test, and harden it before reusing any part of it, deploy only to non-production subscriptions, and never use real customer or personal data.

  A reusable demo pattern for running **Microsoft Foundry** (formerly Azure AI Foundry) hosted agents behind governed model and tool gateways. It is for platform engineers, solution architects, and developers who need to demonstrate - and then adapt - how an agent estate stays governed, observable, and auditable. Version 1.2 runs both hosted agents (Microsoft Agent Framework and LangGraph) on the **official Foundry hosting libraries**, and live-validates both gateways (`apimv2` and the AI Gateway tier, selectable as `apimv2`, `aigateway`, or `both`) end to end on 2026-10-02. Network isolation now creates its private endpoints and DNS zones, but that mode is validated statically only.

## At a glance

| | Item | Value |
|---|---|---|
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="24" alt=""> | **What you get** | Two Foundry hosted agents (`agent-maf`, `agent-langgraph`) calling models and tools only through a gateway. |
| <img src="./docs/assets/icons/container-apps.svg" width="24" alt=""> | **Browser front door** | Deployer-only Entra sign-in; agent prompts, direct gateway/MCP/REST checks, bounded throttling and saved KQL with detailed responses and honest status. |
| <img src="./docs/assets/icons/api-management.svg" width="24" alt=""> | **Default gateway** | <img src="./docs/assets/badges/ga.svg" alt="GA"> Azure API Management Standard v2 - Entra token validation, `llm-*` policies, MCP governance. Live-tested. |
| <img src="./docs/assets/icons/ai-gateway.svg" width="24" alt=""> | **Preview gateway** | <img src="./docs/assets/badges/public-preview.svg" alt="Public preview"> AI Gateway tier (East US 2 / Sweden Central) - runtime `api-key`, model alias, remote and OpenAPI tool servers. Live-tested. |
| <img src="./docs/assets/icons/log-analytics.svg" width="24" alt=""> | **Audit proof** | Structured tool-audit rows, 11 saved KQL queries and a [17-panel workbook](./docs/09-monitoring-and-audit.md#workbook) with token charts, global time range and section-specific trace controls. |
| <img src="./docs/assets/icons/azure-devops.svg" width="24" alt=""> | **Deploy with** | `azd up` (Bicep + hooks + remote builds). Existing environment: `azd provision`, then `azd deploy records-api demo-console` to include the REST collection-routing fix. Console setup/rotation: [03](./docs/03-deployment.md#demo-console-provisioning-and-sign-in). |
| <img src="./docs/assets/icons/code.svg" width="24" alt=""> | **Example domain** | Manufacturing field operations (parts catalog + work orders). Retargetable by configuration only. |

> [!NOTE]
> This README is the front door. Start with [`docs/00-reproduce-this-demo.md`](./docs/00-reproduce-this-demo.md) for the one-page build orchestrator, or jump to the [workshop agenda → doc map](#workshop-agenda--doc-map).

## What this pattern delivers

- Two **Foundry hosted agents** deployed from separate source folders: `src/agents/maf` and `src/agents/langgraph`.
- One **browser demo console** (`src/demo-console`): tenant-only Easy Auth plus a deployer object-ID allowlist; the backend verifies the platform-injected principal ID and rejects conflicting owner/tenant claims when supplied. Browser credentials are not forwarded downstream: the backend uses managed identity, not OBO or an agent identity.
- Three gateway modes: APIM Standard v2 as the default GA path, AI Gateway tier as an opt-in public preview path, or both gateways side by side for validation.
- Governed model routes, native MCP, REST-as-MCP, and REST routes through gateway controls.
- Honest identity/audit comparison: APIM Standard v2 validates Entra tokens; AI Gateway tier preview uses a gateway-scoped runtime access key in the `api-key` header.
- Monitoring with APIM logs, AI Gateway tier telemetry (it lands in the Application Insights `AppRequests` table), OpenTelemetry GenAI spans from both agents, Log Analytics, 11 saved KQL queries, workbook tiles, and structured tool audit records.

> [!NOTE]
> **v1.2 reality check.** On 2026-10-02 both agents on the official hosts passed walkthrough steps S1-S5 through **both** gateways in `eastus2`. The AI Gateway tier is `Microsoft.ApiManagement/service` with sku `AIGateway`, and your subscription needs the `AIGatewayPreview` feature registered first - see [02 - Prerequisites](./docs/02-prerequisites.md#register-the-ai-gateway-preview-feature).

## Pattern at a glance

[![Pattern at a glance](./docs/assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.png)](./docs/assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.png)

<sub>Editable source: [`docs/assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.drawio`](./docs/assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

## What's inside

[![Service catalog](./docs/assets/service-catalog.png)](./docs/assets/service-catalog.png)

<sub>Editable source: [`docs/assets/service-catalog.drawio`](./docs/assets/service-catalog.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

<table>
  <tr>
    <td align="center" width="25%"><img src="./docs/assets/icons/foundry-agent-service.svg" width="48" alt="Foundry Agent Service"><br><b>Foundry Agent Service</b><br><sub>Hosts the two containerised agents (responses 2.0.0).</sub></td>
    <td align="center" width="25%"><img src="./docs/assets/icons/foundry-models.svg" width="48" alt="Foundry Models"><br><b>Foundry Models</b><br><sub><code>gpt-5.5</code> deployment, reached only via a gateway.</sub></td>
    <td align="center" width="25%"><img src="./docs/assets/icons/api-management.svg" width="48" alt="API Management"><br><b>API Management v2</b><br><sub>Default GA gateway: Entra validation, <code>llm-*</code> policies, MCP.</sub></td>
    <td align="center" width="25%"><img src="./docs/assets/icons/ai-gateway.svg" width="48" alt="AI Gateway"><br><b>AI Gateway tier</b><br><sub>Preview gateway: model alias, tool servers, runtime key.</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="./docs/assets/icons/container-apps.svg" width="48" alt="Container Apps"><br><b>Container Apps</b><br><sub>Runs <code>catalog-mcp</code>, <code>records-api</code>, and the deployer-only <code>ca-demo-console</code>.</sub></td>
    <td align="center"><img src="./docs/assets/icons/container-registry.svg" width="48" alt="Container Registry"><br><b>Container Registry</b><br><sub>Stores agent and tool images (remote build).</sub></td>
    <td align="center"><img src="./docs/assets/icons/key-vault.svg" width="48" alt="Key Vault"><br><b>Key Vault</b><br><sub>Holds the AI Gateway runtime key; never in code (env delivery is an explicit demo-only opt-in).</sub></td>
    <td align="center"><img src="./docs/assets/icons/entra-id.svg" width="48" alt="Microsoft Entra ID"><br><b>Microsoft Entra ID</b><br><sub>Gateway app registration; token audience for APIM.</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="./docs/assets/icons/managed-identity.svg" width="48" alt="Managed identity"><br><b>Managed identity</b><br><sub>Gateway-to-Foundry access and the agent instance identity for Key Vault.</sub></td>
    <td align="center"><img src="./docs/assets/icons/log-analytics.svg" width="48" alt="Log Analytics"><br><b>Log Analytics</b><br><sub>Resource-specific tables, saved KQL, retention.</sub></td>
    <td align="center"><img src="./docs/assets/icons/application-insights.svg" width="48" alt="Application Insights"><br><b>Application Insights</b><br><sub>Agent spans, GenAI telemetry, trace correlation.</sub></td>
    <td align="center"><img src="./docs/assets/icons/workbooks.svg" width="48" alt="Workbooks"><br><b>Workbooks</b><br><sub>Dashboard tiles incl. AI Gateway tier telemetry.</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="./docs/assets/icons/alerts.svg" width="48" alt="Alerts"><br><b>Alerts</b><br><sub>Throttling, denial, and error-rate alert rules.</sub></td>
    <td align="center"><img src="./docs/assets/icons/sentinel.svg" width="48" alt="Microsoft Sentinel"><br><b>Sentinel</b> <sub>(optional)</sub><br><sub><code>ENABLE_SENTINEL</code>; workspace onboarding only.</sub></td>
    <td align="center"><img src="./docs/assets/icons/virtual-network.svg" width="48" alt="Virtual Network"><br><b>VNet / Private Link</b> <sub>(optional)</sub><br><sub><code>NETWORK_ISOLATION=true</code> creates private endpoints and DNS (static-only).</sub></td>
    <td align="center"><img src="./docs/assets/icons/content-safety.svg" width="48" alt="Content Safety"><br><b>Content Safety</b><br><sub>Prompt/response screening at the gateway.</sub></td>
  </tr>
</table>

## Gateway modes

[![Gateway modes](./docs/assets/gateway-modes.png)](./docs/assets/gateway-modes.png)

| | Mode | What deploys | Runtime auth | Best use | Recommendation |
|---|---|---|---|---|---|
| <img src="./docs/assets/icons/api-management.svg" width="20" alt=""> | **`apimv2`** <br> <img src="./docs/assets/badges/default.svg" alt="Default"> <img src="./docs/assets/badges/ga.svg" alt="GA"> | APIM Standard v2 / Premium v2, XML policies, LLM API, MCP APIs, REST-as-MCP, REST API. | Entra bearer token for `api://<GATEWAY_APP_CLIENT_ID>`; optional subscription key only for entitlement. | Customer-facing repeatable demos and production-like policy review. | **Default.** Use unless preview tier testing is the explicit goal. |
| <img src="./docs/assets/icons/ai-gateway.svg" width="20" alt=""> | **`aigateway`** <br> <img src="./docs/assets/badges/opt-in.svg" alt="Opt-in"> <img src="./docs/assets/badges/public-preview.svg" alt="Public preview"> | AI Gateway tier public preview resource (`Microsoft.ApiManagement/service`, sku `AIGateway`), model provider, model alias, tool servers, runtime key. | Runtime access key in `api-key`; key is gateway-scoped in preview. | Learning the dedicated AI Gateway tier control plane. | Use only in supported preview regions, with the `AIGatewayPreview` feature registered and preview risk accepted. |
| <img src="./docs/assets/icons/monitor.svg" width="20" alt=""> | **`both`** <br> <img src="./docs/assets/badges/opt-in.svg" alt="Opt-in"> | APIM Standard v2 and AI Gateway tier side by side. APIM remains primary for legacy outputs; AI Gateway tier outputs are also written. | Both mechanisms, selected by `AGENT_DEFAULT_GATEWAY` (passed to the agents as `HOSTED_DEFAULT_GATEWAY`). | Migration/comparison workshops and live validation. | **Recommended for v1.2 validation** - this is the configuration that passed S1-S5 for both agents on both gateways. |

> [!IMPORTANT]
> AI Gateway tier is **public preview**, available in East US 2 and Sweden Central during preview, is created as `Microsoft.ApiManagement/service@2025-09-01-preview` with sku `AIGateway` (it needs the `AIGatewayPreview` feature registered on the subscription), has no SLA, and pricing is to be announced. Manage it in the standalone portal at `ai.gateway.azure.com`. Sources: [overview](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-overview), [quickstart](https://learn.microsoft.com/en-us/azure/api-management/quickstart-ai-gateway-create), [govern/security/operate](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-govern-secure-assets).

## Hosted-agent frameworks

[![Agent frameworks](./docs/assets/agent-frameworks.png)](./docs/assets/agent-frameworks.png)

| | Agent | Source path | Key packages | Host classes | Model client | MCP client | Injected / consumed env vars | Learn reference |
|---|---|---|---|---|---|---|---|---|
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Microsoft Agent Framework** <br> <img src="./docs/assets/badges/protocol.svg" alt="protocol"> | `src/agents/maf` | `agent-framework-core`, `agent-framework-openai`, `agent-framework-foundry-hosting` | `ResponsesHostServer` from `agent_framework_foundry_hosting` (official host; no custom web server) | OpenAI-compatible client pointed at the selected gateway, not direct Foundry. | `MCPStreamableHTTPTool` with gateway headers. | The platform injects `APPLICATIONINSIGHTS_CONNECTION_STRING`, `FOUNDRY_AGENT_INSTANCE_CLIENT_ID` and `FOUNDRY_HOSTING_ENVIRONMENT`; the demo sets `HOSTED_DEFAULT_GATEWAY`, `HOSTED_PROTOCOL`, `HOSTED_RUNTIME`, gateway URLs, `KEY_VAULT_URI`, `AIGW_RUNTIME_KEY_SECRET_NAME` and `AIGW_KEY_DELIVERY`. | [Host Microsoft Agent Framework agents as Foundry hosted agents](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/framework-hosted-agents?pivots=programming-language-python) |
| <img src="./docs/assets/icons/code.svg" width="20" alt=""> | **LangGraph** <br> <img src="./docs/assets/badges/protocol.svg" alt="protocol"> | `src/agents/langgraph` | `langchain-azure-ai[hosting]`, `langchain`, `langchain-openai`, `langchain-mcp-adapters` | `ResponsesHostServer` from `langchain_azure_ai.agents.hosting` (official host) | `ChatOpenAI` pointed at the selected gateway. | `MultiServerMCPClient` with Streamable HTTP gateway URLs; degrades to no tools (logs `mcp_tools_unavailable`) if MCP is unreachable. | Same platform-injected variables and the same `HOSTED_*`, gateway and Key Vault variables as the MAF agent. | [Host LangGraph agents as Foundry hosted agents](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/langchain-hosted-agents) |

Both agents run on the **official Foundry hosts** and declare hosted protocol `responses` version `2.0.0` only (default port 8088); protocol `1.0.0` is not supported. `HOSTED_PROTOCOL=invocations` is a local-only option. Both are deployed with the azd extension `azure.ai.agents` (`host: azure.ai.agent`, `kind: hosted`) and share one gateway-auth and telemetry contract. See [06 - Hosted agents explained](./docs/06-hosted-agents-explained.md).

## Workshop agenda → doc map

| | Segment | What the audience sees | Doc |
|---|---|---|---|
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Hosted agents** | Container contract, sessions, the two frameworks. | [06 - Hosted agents explained](./docs/06-hosted-agents-explained.md) |
| <img src="./docs/assets/icons/entra-id.svg" width="20" alt=""> | **Identity and traceability** | Who called what; token flow; trace correlation. | [07 - Identity, authentication, traceability](./docs/07-identity-auth-traceability.md) |
| <img src="./docs/assets/icons/api-management.svg" width="20" alt=""> | **Tools through the gateway** | Native MCP, REST-as-MCP, allow-lists. | [08 - Tools, APIM, MCP topology](./docs/08-tools-apim-mcp-topology.md) |
| <img src="./docs/assets/icons/log-analytics.svg" width="20" alt=""> | **Monitoring and audit** | Saved KQL, workbook, alerts, audit proof. | [09 - Monitoring and audit](./docs/09-monitoring-and-audit.md) |
| <img src="./docs/assets/icons/virtual-network.svg" width="20" alt=""> | **Enterprise posture and scale** | Network isolation, limits, known gaps. | [10 - Enterprise posture and scale](./docs/10-enterprise-posture-and-scale.md) |
| <img src="./docs/assets/icons/workbooks.svg" width="20" alt=""> | **End-to-end walkthrough** | Browser S1-S5; scripts retained for developer rehearsal and historical evidence. | [11 - Demo walkthrough](./docs/11-demo-walkthrough.md) |
| <img src="./docs/assets/icons/policy.svg" width="20" alt=""> | **Reference and testing** | Every variable, output, test. | [12 - Configuration reference](./docs/12-configuration-reference.md), [04 - Testing](./docs/04-testing.md), [05 - Troubleshooting](./docs/05-troubleshooting.md) |

[![Demo walkthrough story](./docs/assets/demo-walkthrough-story.png)](./docs/assets/demo-walkthrough-story.png)

## Quick start

Provisioning still requires a local CLI session and a **human** signed in to Azure CLI with permission to create Entra apps/credentials. `preprovision` checks the intended tenant/subscription before setup operations, resolves the signed-in human into `AZURE_PRINCIPAL_ID`, and configures a separate single-tenant console app and secret. `postprovision` sets its redirect URI. See [console provisioning](./docs/03-deployment.md#demo-console-provisioning-and-sign-in); never print or share the populated azd environment.

> [!WARNING]
> Replace placeholders with your tenant/subscription. **Never rely on ambient `az` or `azd` state** - both CLIs keep separate logins that drift between tenants. The `preprovision` hook stops the deployment if the `az` context does not match `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID`.

| Step | | Action | Validation |
|---|---|---|---|
| **1** | <img src="./docs/assets/icons/entra-id.svg" width="28" alt="Entra"> | Sign in tenant-explicitly with **both** `azd auth login --tenant-id <TENANT_ID>` and `az login --tenant <TENANT_ID>`; then `az account set`. | - [ ] `az account show` prints the intended tenant + subscription. |
| **2** | <img src="./docs/assets/icons/subscription.svg" width="28" alt="Subscription"> | Register the <img src="./docs/assets/badges/preview.svg" alt="Preview"> `AIGatewayPreview` feature once per subscription (see [02](./docs/02-prerequisites.md#register-the-ai-gateway-preview-feature)), then create the azd environment and set the knobs (`AI_GATEWAY_MODE both`, `MODEL_NAME gpt-5.5`, `DOMAIN_PROFILE manufacturing-field-ops`). | - [ ] `az feature show` reports `Registered`; `azd env get-values` shows the values. |
| **3** | <img src="./docs/assets/icons/container-apps.svg" width="28" alt="Container Apps"> | `azd up` provisions infra, configures console sign-in, and deploys tools + agents + console; agent `postdeploy` grants Key Vault access. | - [ ] Open `DEMO_CONSOLE_URL` as the deployer; inspect each response/status. Isolated mode needs VNet/VPN browser access. |
| **4** | <img src="./docs/assets/icons/api-management.svg" width="28" alt="APIM"> | Validate both gateways with `scripts/validate_gateway.py --target apimv2` then `--target aigateway`. | - [ ] Both targets finish with no failed checks. |
| **5** | <img src="./docs/assets/icons/ai-gateway.svg" width="28" alt="AI Gateway"> | Second pass: `AGENT_DEFAULT_GATEWAY=aigateway` then `azd deploy agent-maf agent-langgraph`. | - [ ] Walkthrough dry-run passes for `--gateway aigateway`. |

<details>
<summary><b>Full command block (copy/paste)</b></summary>

```powershell
azd auth login --tenant-id <TENANT_ID>
az login --tenant <TENANT_ID>
az account set --subscription <SUBSCRIPTION_ID>
az account show --query "{tenant:tenantId, subscription:id, subName:name, user:user.name}" -o table

az feature register --namespace Microsoft.ApiManagement --name AIGatewayPreview --subscription <SUBSCRIPTION_ID>
az feature show --namespace Microsoft.ApiManagement --name AIGatewayPreview --subscription <SUBSCRIPTION_ID> --query properties.state -o tsv
az provider register --namespace Microsoft.ApiManagement --subscription <SUBSCRIPTION_ID>

azd env new <ENV_NAME>
azd env set AZURE_TENANT_ID <TENANT_ID>
azd env set AZURE_SUBSCRIPTION_ID <SUBSCRIPTION_ID>
azd env set AZURE_LOCATION eastus2
azd env set APIM_PUBLISHER_EMAIL <you@example.com>
azd env set AI_GATEWAY_MODE both
azd env set AI_GATEWAY_TIER_LOCATION eastus2
azd env set AIGW_RUNTIME_KEY_SECRET_NAME aigw-runtime-key
azd env set AGENT_DEFAULT_GATEWAY apimv2
azd env set MODEL_NAME gpt-5.5
azd env set MODEL_VERSION 2026-04-24
azd env set MODEL_SKU GlobalStandard
azd env set DOMAIN_PROFILE manufacturing-field-ops

azd up
```

Open the `DEMO_CONSOLE_URL` output and follow [browser S1-S5](./docs/11-demo-walkthrough.md#browser-console-s1-s5). The direct gateway dropdown changes **direct checks only**; agent traffic still uses deployed `HOSTED_DEFAULT_GATEWAY`. OBO and the optional ACA agent comparison remain manual/unavailable unless explicitly deployed. Network isolation is explained with diagrams/manual checks, not simulated live results.

The displayed hosted gateway is a **provisioning snapshot**, not live discovery. When switching `AGENT_DEFAULT_GATEWAY`, reprovision to sync console configuration as well as redeploying agents; agent-only deployment can leave the displayed snapshot stale. S1 invokes Responses only, not a readiness probe; S5 “passed” means rows returned, not a validated audit assertion.

To switch the agents between gateways after the first pass:

```powershell
python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2
python scripts/validate_gateway.py --ids demo-ids.local.json --target aigateway
azd env set AGENT_DEFAULT_GATEWAY aigateway
azd deploy agent-maf agent-langgraph
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway aigateway --dry-run
```

</details>

> [!TIP]
> Model availability and quota change. Re-verify `gpt-5.5` `2026-04-24` (GlobalStandard) in your region before deploying - see the dated matrix in [02 - Prerequisites](./docs/02-prerequisites.md#model-availability-matrix-dated-2026-10-02).

## File index

| | Path | Purpose |
|---|---|---|
| <img src="./docs/assets/icons/code.svg" width="20" alt=""> | `README.md` | Overview, gateway/agent comparison, quick start, distribution, provenance. |
| <img src="./docs/assets/icons/code.svg" width="20" alt=""> | `CHANGELOG.md` | Version history, verification, defects fixed, and live-validation status. |
| <img src="./docs/assets/icons/azure-devops.svg" width="20" alt=""> | `azure.yaml` | azd template with `agent-maf`, `agent-langgraph`, `catalog-mcp`, and `records-api` services. |
| <img src="./docs/assets/icons/resource-group.svg" width="20" alt=""> | `infra/azd.parameters.json`, `infra/azd.bicep` | azd parameter substitutions and subscription-scope wrapper outputs. |
| <img src="./docs/assets/icons/diagnostic-settings.svg" width="20" alt=""> | `infra/hooks/*.ps1` | Tenant guard, AI Gateway tier region guard, local ID writing, runtime-key Key Vault storage, and the `postdeploy` agent-identity Key Vault grant. |
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | `src/agents/maf/` | Microsoft Agent Framework hosted-agent implementation. |
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | `src/agents/langgraph/` | LangGraph hosted-agent implementation. |
| <img src="./docs/assets/icons/code.svg" width="20" alt=""> | `scripts/sync-agent-profiles.ps1` | Copies root profile JSON files into each hosted-agent Docker build context. |
| <img src="./docs/assets/icons/api-management.svg" width="20" alt=""> | `scripts/validate_gateway.py` | Validates APIM v2 or AI Gateway tier runtime routes with `--target`. |
| <img src="./docs/assets/icons/workbooks.svg" width="20" alt=""> | `scripts/demo_walkthrough.py` | Runs/dry-runs the agent x gateway walkthrough matrix. |
| <img src="./docs/assets/icons/query-pack.svg" width="20" alt=""> | `infra/monitoring/queries/11-ai-gateway-tier-telemetry.kql` | AI Gateway tier telemetry (`AppRequests`) comparison query. |
| <img src="./docs/assets/icons/resource-group.svg" width="20" alt=""> | `docs/` | Shareable runbooks; all narrative docs live here. |
| <img src="./docs/assets/icons/resource-group.svg" width="20" alt=""> | `docs/assets/` | Draw.io sources, PNG exports, [product icons](./docs/assets/icons/README.md) and status badges. |

## Distribution

This folder is intended to be checked into Azure DevOps or GitHub as a standalone demo repository. Do not commit populated IDs, tenant/subscription GUIDs, runtime keys, connection strings, `.env` files, or secrets. `demo-ids.template.json` is a shape reference only; the populated `demo-ids.local.json` stays local and gitignored.

> [!CAUTION]
> Never paste the AI Gateway runtime key (or any `listSecrets` output) into docs, issues, chat, or logs. It is gateway-scoped in preview - one key reaches every model and tool.

## Provenance

| | Source | License | Used for |
|---|---|---|---|
| <img src="./docs/assets/icons/api-management.svg" width="20" alt=""> | [`Azure-Samples/AI-Gateway`](https://github.com/Azure-Samples/AI-Gateway) (`1679e31`) | MIT | APIM inference policy and streamable-MCP patterns. |
| <img src="./docs/assets/icons/container-apps.svg" width="20" alt=""> | [`Azure-Samples/fibey`](https://github.com/Azure-Samples/fibey) (`5408f6e`) | MIT | Catalog/inventory MCP service shape. |
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | [`Azure-Samples/simple-foundry-hosted-agent-python-aigateway`](https://github.com/Azure-Samples/simple-foundry-hosted-agent-python-aigateway) (`c572db8`) | MIT | Hosted-agent + AI Gateway wiring. |
| <img src="./docs/assets/icons/resource-group.svg" width="20" alt=""> | [Azure Architecture Icons V24](https://learn.microsoft.com/en-us/azure/architecture/icons/) and [Entra icons](https://learn.microsoft.com/en-us/entra/architecture/architecture-icons) | Microsoft icon terms | Product icons - see [`docs/assets/icons/README.md`](./docs/assets/icons/README.md). |

Upstream samples were used as design references; this demo re-implements the patterns with generic domain data.

## Known gaps

> [!NOTE]
> **Known limitations.** These are open items, not hidden ones.
> - No first-party hosted-agent CI/CD template exists; treat `.github/workflows/deploy.yml` as a starting point only.
> - One Foundry project per environment tier is the supported isolation model.
> - Cross-system trace correlation (agent ↔ gateway ↔ backend) is DIY - the pattern propagates `traceparent` and `x-gw-request-id`, but there is no single platform join.
> - The effective runtime identity of a hosted agent is its **instance identity**, which exists only after the agent is deployed, so Bicep cannot grant it Key Vault access. The `postdeploy` hook does it, but that hook is not yet verified live.
> - Under an organization policy that disables Key Vault public network access, hosted agents (which run outside your VNet) get `ForbiddenByConnection` on Key Vault. The proper fix is network isolation mode; `AIGW_KEY_DELIVERY=env` is a demo-only compromise that stores the key in plaintext in the azd env and agent configuration.
> - `NETWORK_ISOLATION=true` now creates private endpoints and DNS zones, but it is validated by `what-if` only (127 resources, no errors) and was never live-deployed. The hosted-agent endpoint stays public, APIM and the AI Gateway tier stay public until a manual lockdown, and there is no AMPLS. See [10 - Enterprise posture and scale](./docs/10-enterprise-posture-and-scale.md).
> - The AI Gateway tier writes its LLM and MCP telemetry to Application Insights `AppRequests`, not to `ApiManagementGatewayLlmLog`; only the 429 policy probe was exercised among its policies.

> [!IMPORTANT]
> **Validation status (2026-10-02, `eastus2`):** both gateways were live-tested. Both hosted agents (official MAF and LangGraph hosts) passed walkthrough steps S1-S5 through **APIM Standard v2** and through the **AI Gateway tier**, and all 11 saved KQL queries executed. **Network isolation** is static-only. See [Live validation](./docs/04-testing.md#live-validation-2026-10-02) and `CHANGELOG.md`.

## Decision provenance

| Date | Decision | Reference |
|---|---|---|
| 2026-09-30 | Locked v1 demo pattern for Foundry hosted agents behind APIM AI Gateway with governed MCP/REST tools and audit-first landing-zone posture. | `CHANGELOG.md` 1.0.0 entry. |
| 2026-10-01 | v1.1 adds AI Gateway tier preview sidecar and dual hosted-agent frameworks while keeping APIM Standard v2 the safe default. | This docs update and `CHANGELOG.md` 1.1.0 entry. |
| 2026-10-02 | Visual documentation pass: product icons, status badges, callouts, step cards. | [`docs/assets/icons/README.md`](./docs/assets/icons/README.md). |
| 2026-10-02 | v1.2 moves both agents to the official Foundry hosts, live-validates the AI Gateway tier (`Microsoft.ApiManagement/service`, sku `AIGateway`), and adds isolation-mode private endpoints (static-only). | `CHANGELOG.md` 1.2.0 entry and [04 - Testing](./docs/04-testing.md#live-validation-2026-10-02). <img src="./docs/assets/badges/live-tested.svg" alt="Live-tested"> |

## Disclaimer

> [!CAUTION]
> This project is provided for testing, learning, and demonstration purposes only. It is not an official Microsoft product, sample, or service, and it is not supported under any Microsoft support program. Azure services, APIs, and pricing referenced here change over time — validate against current Microsoft Learn documentation before relying on any detail. Deploying it creates billable Azure resources; you are responsible for their cost, security, and cleanup.

## License

> [!NOTE]
> Released under the [MIT License](LICENSE).

---

*Last updated: 2026-10-15*
