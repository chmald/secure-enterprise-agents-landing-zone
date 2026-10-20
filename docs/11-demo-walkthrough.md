[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 11 Demo walkthrough

# 11 - Customer session guide and demo walkthrough

<p>
  <img src="./assets/icons/foundry-agent-service.svg" width="40" alt="Foundry Agent Service"/>&nbsp;
  <img src="./assets/icons/entra-workload-id.svg" width="40" alt="Entra workload identity"/>&nbsp;
  <img src="./assets/icons/toolbox.svg" width="40" alt="Toolbox and MCP tools"/>&nbsp;
  <img src="./assets/icons/api-management.svg" width="40" alt="API Management"/>&nbsp;
  <img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway"/>&nbsp;
  <img src="./assets/icons/virtual-network.svg" width="40" alt="Virtual Network"/>&nbsp;
  <img src="./assets/icons/log-analytics.svg" width="40" alt="Log Analytics"/>&nbsp;
  <img src="./assets/icons/workbooks.svg" width="40" alt="Workbooks"/>
</p>

![GA](./assets/badges/ga.svg) ![Preview](./assets/badges/preview.svg) ![live-tested](./assets/badges/live-tested.svg) ![version](./assets/badges/version.svg)

A generic discovery-to-pilot session guide for the hosted-agent and AI gateway landing zone. The **eight-item agenda** combines customer discussion, reference architecture and bounded live evidence. The existing **S1-S5 execution workflows** remain the technical core: two agent frameworks (Microsoft Agent Framework and LangGraph), two gateway targets (APIM v2 and the AI Gateway tier), tools and audit.

**No customer current state, requirements, named owners or approvals are established by this repository.** All customer-specific answers below are **unknown / to agree**. The `manufacturing-field-ops` profile is a synthetic example, not a description of a customer's environment. Keep confidential discovery answers and decisions in the customer's approved private engagement record, not in this public demo.

> [!IMPORTANT]
> **Use APIM for the current session; keep preview deferred.** The later [APIM-focused validation](./04-testing.md#apim-focused-hosted-read-validation-2026-10-20) completed both hosted read scenarios and verified actual tool results, agent-instance identity and selected trace joins. The real gateway is **Basic v2**, while azd still requests Standard v2; no tier change was made. This does not establish a human-browser acceptance pass, writes, throttling or private-network capabilities. The badges and 2026-10-02 matrix below remain historical **script-driven** evidence. Open `DEMO_CONSOLE_URL` for presentation; no local demo scripts are needed.

## At a glance

| | Item | Detail |
|---|---|---|
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""/> | **Audience** | Platform, security and application owners deciding how to govern agents. |
| <img src="./assets/icons/container-apps.svg" width="24" alt=""/> | **Driver** | Browser at `DEMO_CONSOLE_URL`, signed in as the deploying human. Scripts below remain a separate developer/rehearsal path. |
| <img src="./assets/icons/policy.svg" width="24" alt=""/> | **Session guide** | Collapsed presenter guide above the five S1-S5 tabs; discussion is separate from live proof, with the maintained reference architecture shown inside the guide. |
| <img src="./assets/icons/log-analytics.svg" width="24" alt=""/> | **Evidence** | Readable S5 query labels: 01 audit, 02 tokens, 04 trace, 11 gateway/agent observations ([doc 09](./09-monitoring-and-audit.md)). |
| <img src="./assets/icons/workbooks.svg" width="24" alt=""/> | **Workbook** | S5 links to the deployed workbook when `WORKBOOK_ID` is configured; otherwise it shows the missing configuration honestly. Workbook and alert evidence still require portal inspection. |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""/> | **Preview lane** | Deferred for the current session and validation scope. Historical ![Public preview](./assets/badges/public-preview.svg) comparison material is retained, not promoted to new acceptance. |

## Objectives and success criteria

These are **proposed session exit criteria**, not pre-approved customer requirements or claims that the demo has already passed them.

| Objective | Observable exit criterion | Evidence limit |
|---|---|---|
| Establish scope | Record one representative workflow, its intended outcome and unresolved requirements in the discovery scaffold. | Customer answers and success thresholds are unknown / to agree. |
| Explain architecture and identity | Identify browser, console MI, agent-instance, delegated console user and gateway principals, plus the API/backend authorization boundary. | Sign-in alone is not OBO. The explicit console exchange is not hosted-agent delegation; JWT acceptance, delegated scope and a tool allowlist are not per-user record authorization. |
| Inspect bounded technical evidence | For each approved operation, record actual route, response/run status, tool result and relevant log rows; distinguish missing evidence. | A completed agent response does not prove tool choice; a 429 does not establish its policy origin; KQL rows do not validate an audit assertion. |
| Define a candidate validation | Draft one read-only-first pilot card with prerequisites, acceptance checks, exclusions and approval gate. | No customer pilot, deployment or data access is approved here. |
| Close accountably | Record each decision or open question with status, owner role, named owner and next review. | Every customer-specific assignment, decision, approval and date remains unknown / to agree until confirmed. |

## Eight-item customer session agenda

Use this order for the session; do not turn eight discussion topics into eight invented execution buttons. S4 is an optional, separately approved technical exercise, not a prerequisite to discussing architecture or a pilot.

| # | Session topic | Discussion or live proof | Session output / reference |
|---|---|---|---|
| 1 | Objectives and success criteria | **Discussion** | Agree scope and proposed evidence checklist; customer thresholds unknown / to agree. |
| 2 | Current-state architecture and requirements through a representative scenario | **Discussion**, then synthetic scenario | Fill the [discovery scaffold](#current-state-discovery-scaffold); distinguish customer reality from sample parts/work orders. |
| 3 | Foundry Hosted Agents' architectural fit | **Discussion**; approved S1 is limited live proof | Compare hosted, prompt and self-hosted choices in [doc 06](./06-hosted-agents-explained.md); a completed Responses run proves protocol behavior, not customer fit. |
| 4 | Agent identity, authentication and user-versus-agent authorization | **Discussion** plus approved S2 checks | Compare four S2 cards: anonymous 401, console MI catalog discovery, hosted instance identity via S1/S5, and explicit optional console-to-APIM user OBO. |
| 5 | APIM/MCP integration through downstream APIs/systems | **Discussion** plus approved S3 reads | Inspect live tools/schema and sample results; map potential customer interfaces without claiming they are connected ([doc 08](./08-tools-apim-mcp-topology.md)). |
| 6 | End-to-end traceability, monitoring and audit | **Evidence inspection**, S5 and optional portal views | Use 01/04 for audit/trace and 02/11 for token sources; record missing joins and unavailable sources ([doc 09](./09-monitoring-and-audit.md)). |
| 7 | Reference architecture and potential pilot/validation | **Discussion** | Review the maintained reference diagram and [candidate pilot](#candidate-read-only-first-pilot); no production or isolated-network acceptance is implied. |
| 8 | Questions, decisions, owners and next steps | **Discussion / closeout** | Use the [closeout template](#open-questions-decisions-and-closeout); assignments and approvals unknown / to agree. |

## Current-state discovery scaffold

Ask these during the session, not as a prerequisite to presenting the generic demo. Do not infer answers from the sample profile or fill them into committed documentation.

| Discovery area | Questions to resolve | Customer answer |
|---|---|---|
| Workflow and outcome | Who initiates the workflow? What decision or task should improve? Which measurable outcome matters? | Unknown / to agree |
| Current architecture | Which agents, orchestrators, models, gateways, environments and systems already exist? Which component would change? | Unknown / to agree |
| Downstream interfaces | Which API/MCP surfaces are available? Who owns their schemas, sandbox, read/write permissions and lifecycle? | Unknown / to agree |
| Identity and authorization | Is the caller a human or autonomous workload? Is delegated authorization required? Where are action- and record-level entitlements enforced? | Unknown / to agree |
| Data and privacy | What classification, residency, prompt/content logging, retention and redaction constraints apply? | Unknown / to agree |
| Network and security | Which paths must be private? How must backends authenticate the gateway? What content-safety and security controls require validation? | Unknown / to agree |
| Operations and validation | Who operates traces, alerts, access reviews, deployment and rollback? What load, quality and acceptance thresholds apply? | Unknown / to agree |

## Synthetic representative scenario

**Sample only:** a field operator checks parts availability and reviews existing work orders before deciding whether a new work order is needed. Use `manufacturing-field-ops` disposable seed data, not customer inventory, records or people.

1. Start with direct S3 MCP discovery. Inspect `list_items` / `search_items` and `list_records`; use identifiers actually returned by a list before `get_item`, `check_availability` or `get_record`. Tool names may differ by gateway; use the live schema.
2. If an agent invocation is separately approved, use the canonical manufacturing S3 prompt: “**Check availability of 2 units of PRT-100 for a synthetic line inspection. Use catalog tools only; do not create or update data.**” This quantity and scenario are synthetic, not customer requirements. Review records separately through direct reads. **Prompt wording is not a read-only security control:** the agent can choose mutating tools, so every submission still requires confirmation.
3. Direct reads demonstrate the console's protocol path. An agent answer must be checked against actual tool/audit rows before claiming the agent used a particular tool or gateway.
4. A create/update is an **optional separate exercise**, requiring explicit authorization, disposable data and verification afterward. It is not required for the read-only-first session or candidate pilot.

## Runtime and identity fit boundaries

| Boundary / choice | What this demo can explain or inspect | What it does not establish |
|---|---|---|
| Hosted runtime | Two framework implementations use the official Responses contract; hosted versus self-hosted trade-offs are in [doc 06](./06-hosted-agents-explained.md). | Customer runtime selection, quality, capacity, private deployment or production readiness. Customer fit unknown / to agree. |
| Browser → console | Primary deployer-only single-tenant Easy Auth; backend validates the trusted platform principal and any supplied conflicting claims. | Sign-in alone does not delegate the human or implement multi-user business authorization. The exact OBO form-post callback has independent binding/state/tenant/deployer validation. |
| Console → agent / default APIM | Backend MI invokes agents; default direct APIM checks present the console MI token. Hosted agents independently use their deployed app-only instance identities. | A direct MI check is not evidence of agent identity, tool choice or human delegation. |
| APIM → tool/backend | JWT validation, sanitized gateway headers and a global tool allowlist on the gateway path. | Per-user/action/record entitlements or a production trust boundary. Public backend ingress/trust is a demo limitation; production needs independently validated backend access/authentication. |
| Preview tier | Gateway-scoped runtime key; gateway MI for the model; current token source is **AI Gateway - Foundry-observed**. | Per-human/per-agent runtime validation, APIM-only REST/denial parity, native metric export or token-limit enforcement. |
| Content safety | The preview tier has configured content-safety cards. Query 09/alerts can surface candidate filtering/block signals. | The APIM sample does **not** implement `llm-content-safety`; a model filter, error keyword or 403 is not proof of APIM enforcement. |
| Explicit console → APIM user OBO | Optional A → B → C server-side user token exchange, followed only by catalog MCP discovery. Inspect trace-matched human/caller audit fields. | No hosted-agent user delegation, model cost, record write, customer-system integration, per-user/action/record authorization or agent-routing switch. The legacy `obo-client` sample only signs into Foundry. |

## Candidate read-only-first pilot

This is a **proposal scaffold**, not a customer plan or an approved commitment.

| Pilot field | Generic candidate | Customer decision / approval |
|---|---|---|
| Scope | One selected workflow and one sandbox API/MCP boundary; synthetic data and read-only operations first. | Unknown / to agree |
| Runtime and gateway | Evaluate a hosted-agent candidate with APIM as the reference lane; preview tier comparison only if accepted. | Unknown / to agree |
| Prerequisites | Confirm backend access/trust, identity and business authorization, network/data rules, tool schema, logging/privacy and sandbox access. | Unknown / to agree |
| Acceptance | Record one completed approved agent run; verify its actual tool/route and linked audit evidence; compare returned sample values with source data. Any required missing hop remains unresolved. | Customer quality, latency, load and completeness thresholds unknown / to agree |
| Token evidence | Separate gateway/backend observations from agent spans; use identity-matched Foundry counters for the tier and retain unavailable native export honestly. | Required attribution and cost reporting unknown / to agree |
| Safeguards / exclusions | No customer data, automatic writes, production traffic, assumed OBO, production-security certification or load benchmark. Optional writes require separate approval and rollback. | Data access, optional writes and rollback approval unknown / to agree |
| Ownership and gate | Identify architecture, identity, API and operations owners before scheduling validation; agree stop/go criteria and next review. | Owner roles, names, dates and approval unknown / to agree |

## Open questions, decisions and closeout

Record the result privately; do not pre-populate customer answers in this repository.

| Question / proposed decision | Status | Evidence / gap | Owner role | Named owner | Next review |
|---|---|---|---|---|---|
| Representative workflow, outcome and success thresholds | Unknown / to agree | Customer current state and requirements unknown / to agree | Unknown / to agree | Unknown / to agree | Unknown / to agree |
| Runtime, gateway and user/agent authorization model | Unknown / to agree | Demo boundaries above; customer fit unknown / to agree | Unknown / to agree | Unknown / to agree | Unknown / to agree |
| Sandbox API/MCP integration and backend trust | Unknown / to agree | Customer endpoint, schema and authorization unknown / to agree | Unknown / to agree | Unknown / to agree | Unknown / to agree |
| Audit/privacy requirements and missing evidence | Unknown / to agree | Record observed rows and missing joins; customer requirements unknown / to agree | Unknown / to agree | Unknown / to agree | Unknown / to agree |
| Candidate pilot scope, safeguards and approval gate | Unknown / to agree | No customer pilot or access approval established | Unknown / to agree | Unknown / to agree | Unknown / to agree |

## The story

[![Demo walkthrough story](./assets/demo-walkthrough-story.png)](./assets/demo-walkthrough-story.png)

<sub>Editable source: [`assets/demo-walkthrough-story.drawio`](./assets/demo-walkthrough-story.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

## Browser console S1-S5

### Before presenting

- Select **APIM v2 (Entra)**. Both current hosted definitions use APIM; preview comparison is out of scope for this session. Verify the [live-tier drift](./04-testing.md#apim-focused-hosted-read-validation-2026-10-20) before provisioning: the live service is Basic v2, not evidence of Standard v2 isolation capabilities.
- Expand the collapsed **session/presenter guide** to frame discussion separately from live proof. Its reference image is served at `/reference/architecture.png` from the maintained architecture PNG bundled with the console image; it is not live topology discovery. The guide does not replace the five S1-S5 tabs.
- New environments use `azd up`. For the **current Basic-v2/StandardV2-drifted environment, do not run full `azd provision` or upgrade/change SKU/preview**. Apply only approved configuration/auth/APIM policy updates in [doc 03](./03-deployment.md#optional-console-to-apim-user-obo), then separate `azd deploy catalog-mcp`, `azd deploy records-api` and `azd deploy demo-console` calls. The CLI accepts one service argument per deploy. Check in-memory records are unchanged seed data before backend restarts; otherwise stop and agree preservation/rollback. The app never shells out to CLI/scripts.
- Sign in as the **deploying human**. Single-tenant Easy Auth plus its deployer-object-ID allowlist gates access; the backend verifies ACA's platform-injected principal ID and rejects conflicting claims when supplied. A second user in the same tenant is not automatically allowed.
- If `NETWORK_ISOLATION=true`, use a browser connected to the VNet/VPN with working private DNS: the console shares the internal ACA environment.
- Use only disposable sample data. **Every agent submission requires confirmation**, because an agent can choose mutating tools regardless of how harmless the prompt sounds. Confirm direct writes and throttle bursts separately. No writes run automatically.
- Show the **agent gateway provisioning snapshot** (`HOSTED_DEFAULT_GATEWAY`) separately from the **direct gateway selector**. The selector changes direct checks only; it does not reroute MAF/LangGraph. This is not live discovery: changing `AGENT_DEFAULT_GATEWAY` with an agent-only deploy can leave the console stale. Any approved route change must synchronize console config and agents, but is not part of this bounded update; do not full-provision the current drifted environment.
- Action buttons remain disabled until configuration loads. Configuration exposes available gateways and a provisioning snapshot, **not live agent readiness**. If it fails to load, diagnose configuration/access rather than treating disabled controls as a passed check.
- Keep detailed **redacted** responses and trace IDs available. Never expose credentials, access tokens, authorization codes, cookies or populated azd environment values in a recording. Business data is synthetic, but the actual signed-in operator's name/username/object ID is privacy-relevant: do not screen-record or share unredacted identity/audit evidence.

### S1 — Submit a real hosted-agent prompt

Choose **MAF** or **LangGraph**, enter a prompt for the demo profile, review it, confirm potential tool/data changes, and submit only when authorized. Repeat with the other framework if desired and approved. **S1 invokes Responses only; it does not issue a readiness GET.** Inspect the returned response and require a completed run status, not just HTTP 200 (the host can include a failed status inside a successful HTTP response).

**Say:** “This response demonstrates the hosted transport/protocol path for the selected framework. The agent uses its deployed gateway configuration.” It does **not** prove a specific tool was selected, that all calls used the dropdown's gateway, or that `traceparent` propagated. Verify actual tool use and correlation in logs at S5. Header trace IDs are advisory handles, not propagation proof.

### S2 — Compare four caller identities

Keep **APIM v2** selected for this session. S2 intentionally separates four cards instead of inferring a user or agent identity from a generic “authenticated” result:

| Card | Operation / credential | What it can establish |
|---|---|---|
| **1 — Anonymous** | No credential to the selected gateway | Expected **401** for this request. It does not prove every route, backend or business operation is secured. |
| **2 — Console managed identity** | Read-only APIM catalog MCP discovery using the console MI token (`https://cognitiveservices.azure.com`) | The console workload called the catalog. No delegated human and no hosted-agent principal are implied. |
| **3 — Hosted-agent instance identity** | Explain/inspect an independently approved **S1** run and its **S5** evidence; no agent run is silently launched by this card | Hosted agents remain **app-only** as their instance identities. A human starting S1 does not delegate that human downstream. |
| **4 — Console-to-APIM user OBO** | Explicit opt-in sign-in, server-side A → B → C token exchange, then read-only catalog MCP discovery | A human can be attributed only when the **same probe trace** has the validated delegated identity in downstream audit. Token metadata alone is not that proof. |

The MI/OBO probes perform only **`initialize`, `notifications/initialized`, `tools/list`** on catalog MCP: **no model request/cost, business-tool call or record write**. S1 remains separately confirmed and can incur model cost or mutate data. The preview lane remains unchanged/deferred; its gateway-scoped `api-key` proves possession, not per-user/per-agent identity, and it has no user OBO parity.

#### Configure and run the explicit user OBO comparison

1. Complete [doc 03's opt-in setup](./03-deployment.md#optional-console-to-apim-user-obo). `ENABLE_DEMO_OBO` defaults to `false`. Auxiliary confidential client **A** (`DEMO_OBO_CLIENT_ID` / `obo-signin-secret`) obtains a user **access token for existing console API B**, scope **`api://<B>/Console.Access`**. B uses **its own existing credential** (`DEMO_CONSOLE_CLIENT_ID` / `entra-client-secret`) for MSAL OBO toward **C** (`GATEWAY_APP_CLIENT_ID`), scope **`api://<C>/Gateway.Access`**. No ID token or self-audience sign-in shortcut substitutes for that assertion.
2. Sign into the normal console as the deploying human, then explicitly start S2 user OBO and complete Entra sign-in as that **same allowed deployer**. The exact **`POST /api/identity/obo/callback`** uses standard `form_post`; only this route is excluded from platform login. Its Secure/HttpOnly/SameSite=None `__Host-` browser-binding cookie, MSAL state/nonce/PKCE, tenant and deployer checks precede exchange/probe. All other routes retain Easy Auth and normal custom-header/exact-Origin CSRF controls.
3. Keep the parent console open. It polls the protected result endpoint and keeps the single console replica active. Flow/result state is memory-only, **10/5 minutes**; restart, expiry, cancellation or replay fails closed. Grant/consent failures are explicit; there is **no MI fallback**. Raw access tokens and client secrets stay server-side; authorization codes are not callback URL query parameters.
4. Inspect the catalog-discovery result and safe acquired-token metadata. Names/usernames are optional actual claims; `oid` is the stable/authoritative human identifier. This operation is **not hosted-agent delegation or user/record-level business authorization**.
5. Choose **“Read this identity call's audit”**. It reads source query **01 filtered by this probe's trace ID**. Wait for ingestion if necessary; inspect `identity_type`, `human_oid`, optional `human_name` / `human_username`, `delegated_scopes`, plus `agent_appid` / `agent_oid`. Those last fields have historical names: for OBO they describe console API B/the token subject, **not an independent hosted agent**. Do not substitute a successful MI/agent trace or unrelated recent rows.

**Acceptance boundary:** configured apps/scopes/callbacks, a valid authorization URI, token metadata or a local/browser fixture pass do not establish a live user OBO/audit pass. Record actual human sign-in and matching downstream evidence in [doc 04](./04-testing.md) before presenting that result as verified. Do not expose real operator auth metadata in a recording or share it unredacted.

### S3 — Discover tools, then invoke explicitly

1. Select **catalog** or **records** MCP on the chosen direct gateway. Initialize the MCP session and list tools; inspect the actual names and live `inputSchema`.
2. Choose an **enabled business tool**. The console generates JSON arguments from that live schema; inspect and edit values before invoking. Do not assume names match between gateways. Unsupported advertised operations stay visible but disabled / not demo-enabled; discovery JSON retains the full schema. For example, the tier advertises `records_healthz_healthz_get` in addition to the four supported records business tools; advertising it does not enable a console action or change the backend allowlist.
3. For known mutating tools **`create_record` / `update_record`**, explicitly check the write-confirmation box. Use sample records only. No discovery action or page load automatically invokes a write.
4. For direct **REST**, use **APIM only**: list/get/create/update records with JSON arguments. The gateway collection URL is **`/records/`**, not `/records/records`. Review record identifiers and confirm creates/updates separately.
5. On **APIM only**, run the denied-tool probe and inspect the expected **403 allowlist denial**. An unrelated 403 is not proof of that policy. REST and denied-tool controls are disabled when the tier is selected; these paths are **`unavailable`**, not equivalent tier enforcement.

Direct MCP/REST calls show direct protocol behavior, not what the agent chose to do in S1. Use S5 to check the audit trail. REST and denied-tool APIM-only controls must not be presented as tier parity.

### S4 — A bounded throttle probe, plus a manual posture discussion

Review and explicitly confirm the burst: **1-120 calls**, **concurrency ≤8**, a **≤90-second dispatch window** and **≤15-second per-request timeout**. Requests already underway may finish at the dispatch deadline; not all requested attempts must run. One console replica is configured. This consumes model capacity and can cause throttling/cost. Show detailed responses and the selected gateway's reason.

- Observed **429** is evidence that throttling occurred on this request path; do **not** infer whether the source was token limits, request-rate limits or an upstream service without logs.
- **No observed 429 = `not_run`, not `passed`.** The bounded burst did not establish the throttle condition; do not automatically increase the load or repeat indefinitely.
- For network posture, show the [network topology](./10-enterprise-posture-and-scale.md#the-network-path) and explain deployed/manual validation boundaries. The console does **not** manufacture private-link or network-isolation live checks.

### S5 — Run bounded saved KQL and inspect actual evidence

Choose a readable saved-query label **01-11** (fixed allowlist; no arbitrary KQL), run it, and display the returned rows and trace ID. The console sets a **one-hour timespan on the query API** and appends **`take 200`**. **“Passed” means rows returned, not a validated audit assertion**; inspect the contents to establish evidence.

- Use **APIM 01 - Who called which tool** and **04 - End-to-end trace** as the **primary session trace proof**: selected catalog/records and [scoped hosted-read requests](./04-testing.md#apim-focused-hosted-read-validation-2026-10-20) have their own source evidence. S2's **“Read this identity call's audit”** instead filters 01 by that specific identity probe's trace ID; inspect human fields/scopes/caller, not just returned-row count. A direct OBO discovery has no hosted-agent or model hop. Selected **preview** traces show `AppRequests` / `AppDependencies` but **no joined backend `tool_audit` hops**; present that as incomplete end-to-end correlation, never a full trace pass. Use **02 - Token usage by agent and user** and **11 - AI Gateway tier telemetry** to compare sources.
- APIM `catalog-mcp` / `records-mcp` are HTTP policy proxies (`apiType=http`) to backend MCP adapters. Records MCP wraps the same record business functions; only the **preview records** tool server uses OpenAPI generation and dispatches REST. Native MCP query **05 is conditional** and can have no events for these APIM HTTP APIs; keep it intact, with no fake fallback or broken-wiring claim.
- Tier requests remain in `AppRequests`; verified tier token counts come from identity-matched Foundry `RequestResponse` logs, labeled **AI Gateway - Foundry-observed**. Native request-log counters/metric export remain unavailable. The 2026-10-19 sample was **26 input / 21 output across two calls**, not a current-hour guarantee or per-human/per-agent attribution. Do not add these observations to agent-span totals.
- A response-header trace ID is advisory: inspect returned spans/audit rows to verify correlation; missing joins must not be described as propagated.
- **Empty results = `not_run`**, with ingestion-delay/no-evidence guidance. Wait a few minutes and rerun; absence of rows is not an audit success.
- Use S5's workbook link when `WORKBOOK_ID` is configured; otherwise the missing configuration is shown and no workbook proof is implied. Workbooks/alerts remain portal surfaces, not simulated console results. User OBO is the separately configured S2 path; the optional ACA agent comparison remains separate/manual.
- In the workbook, start with the two token charts, then use the labeled evidence sections. Its time range is global; trace input is local to Trace investigation. Check numeric `/ input` and `/ output` totals and real date/time ticks, not JSON array labels. The workbook is separate from console S5's fixed one-hour query window. Use the [visual acceptance checklist](./04-testing.md#workbook-visual-acceptance) before presenting.

### Reading the console status

Each operation shows detailed response data and one of **`passed`**, **`failed`**, **`unavailable`**, **`not_run`**. A pass applies to that operation's observed transport/protocol condition only. Failure needs response/log inspection; unavailable means unsupported/not deployed; not_run includes skipped or unobserved evidence. Do not turn unavailable or missing evidence into green “end-to-end security” claims.

## Developer/script path (separate from the console)

> [!NOTE]
> The remaining run-of-show, command matrix and live evidence retain the earlier script workflow. They do not describe code executed by the console. The explicit S2 OBO flow is implemented in the console, **not** the legacy user-to-Foundry sign-in sample or developer walkthrough runner; the optional ACA comparison needs its own deployment. Current dry-run prints **`PLAN`**; unimplemented script S2-S5 report **`NOT_RUN`**. Neither is PASS, and an incomplete live run exits **2**. Only an actually invoked S1 with a completed Responses payload can pass its protocol check. `--gateway` labels the **expected route**; it never reconfigures deployed agents or proves their route.

## Run of show

Historical technical rehearsal outline (about 40 minutes), **not** the eight-item customer agenda above. S2-S5 proof requires separately executed checks; a script step label or dry-run endpoint is not evidence.

| Segment | Time | | What to show | Proof |
|---|---|---|---|---|
| **Open** | 3 min | <img src="./assets/icons/foundry.svg" width="24" alt=""/> | The architecture diagram and the two-gateway idea. | The hero row: agents, gateways, tools, audit. |
| **S1 Hosted agents** | 6 min | <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""/> | When separately authorized, both agents use the same synthetic prompt through the Responses contract. | Inspect completed response payloads; `/readiness` is a separate contract check, not an agent-text assertion. |
| **S2 Identity** | 7 min | <img src="./assets/icons/entra-workload-id.svg" width="24" alt=""/> | Missing credentials are refused; identify the actual authenticated caller in separately collected evidence. | `401` without credentials; inspect recorded principal/caller and trace fields, without assuming OBO. |
| **S3 Tools / MCP** | 8 min | <img src="./assets/icons/toolbox.svg" width="24" alt=""/> | APIM HTTP proxies to backend MCP adapters; optional separately authorized mutation and denied-tool probe. | Actual backend `tool_audit` and HTTP gateway rows; no native query-05 requirement for these proxies. |
| **S4 Scale / posture** | 6 min | <img src="./assets/icons/virtual-network.svg" width="24" alt=""/> | An explicitly approved bounded probe; the network-isolation diagram. | Inspect any observed `429` and its source; topology is design/manual evidence, not a live isolation pass. |
| **S5 Observability** | 8 min | <img src="./assets/icons/log-analytics.svg" width="24" alt=""/> | The audit query, the trace query, the workbook and the alert. | Query 01 and query 04 results; the workbook tiles. |
| **Close** | 2 min | <img src="./assets/icons/policy.svg" width="24" alt=""/> | Preview versus GA (![GA](./assets/badges/ga.svg) vs ![Public preview](./assets/badges/public-preview.svg)), and next steps. | The status table in the [README](../README.md). |

> [!TIP]
> Open S5 in Log Analytics **before** the session starts and run query 01 once so the workspace is warm. Query results lag ingestion by a few minutes; do not rely on records from the call you just made.

## The agent by gateway matrix

Each cell is one script rehearsal command. Checkmarks below preserve the historical 2026-10-02 report ([live evidence](#live-evidence)), not current script status or a browser-console matrix. A current dry-run prints `PLAN`; `--gateway` is expected-route labeling only.

| Agent | Gateway | Dry run | Live |
|---|---|---|---|
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""/> **MAF** | <img src="./assets/icons/api-management.svg" width="20" alt=""/> APIM v2 | ✅ `python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent maf --gateway apimv2 --dry-run` | ✅ |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""/> **LangGraph** | <img src="./assets/icons/api-management.svg" width="20" alt=""/> APIM v2 | ✅ `python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent langgraph --gateway apimv2 --dry-run` | ✅ |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""/> **MAF** | <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> AI Gateway tier ![Preview](./assets/badges/preview.svg) | ✅ `python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent maf --gateway aigateway --dry-run` | ✅ |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""/> **LangGraph** | <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> AI Gateway tier ![Preview](./assets/badges/preview.svg) | ✅ `python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent langgraph --gateway aigateway --dry-run` | ✅ |
| **Both agents** | Selected gateway | ✅ `python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway apimv2 --dry-run`; repeat with `aigateway` | ✅ |

## Walkthrough steps

### S1 - Hosted agents

| Step | | Action | Validation |
|---|---|---|---|
| 1 | <img src="./assets/icons/foundry-agent-service.svg" width="28" alt=""/> | When authorized, run `python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway apimv2 --step S1`. The flag labels the expected route, not a routing change. | - [ ] Each actually invoked Responses run reports completed status; verify routing/tool use separately in logs. Readiness is a separate contract check. |
| 2 | <img src="./assets/icons/container-apps.svg" width="28" alt=""/> | Optional: show the same image on Container Apps (`DEPLOY_AGENT_ON_ACA=true`). | - [ ] The hosted and Container Apps runtimes give the same answer. |

**Expected result:** two frameworks, one contract. **Proof:** an executed, completed Responses payload plus relevant logs. A constructed endpoint in dry-run is `PLAN`, not proof.

### S2 - Identity

| Step | | Action | Validation |
|---|---|---|---|
| 1 | <img src="./assets/icons/entra-id.svg" width="28" alt=""/> | Call the gateway with **no token**. | - [ ] The response is `401`. |
| 2 | <img src="./assets/icons/entra-workload-id.svg" width="28" alt=""/> | Separately invoke through the gateway with a known caller's token and `traceparent`. | - [ ] Inspect which principal actually called; a CLI or console identity is not an agent identity. |
| 3 | <img src="./assets/icons/enterprise-applications.svg" width="28" alt=""/> | For a delegated comparison, use the separately configured **console S2 user OBO**, not the script runner or legacy `obo-client` sign-in sample. | - [ ] Require this probe's trace-matched human/caller audit. It is not hosted-agent user delegation. |

**Expected result:** the APIM path shows the actual Entra caller; the AI Gateway tier path shows its runtime-key limitation (`caller="aigw-runtime-key:agents"`, no agent principal). **Proof:** inspect `gateway`, `caller`, historical `agent_principal`, `identity_type`, `human_principal` and `delegated_scopes`. User attribution requires the explicitly executed console OBO trace, not a human initiating an agent call.

> [!TIP]
> Say it plainly: "Runtime keys prove possession of a gateway key; they do not identify a human or agent principal." This is the single most important difference between the two gateways.

### S3 - Tools and MCP

| Step | | Action | Validation |
|---|---|---|---|
| 1 | <img src="./assets/icons/toolbox.svg" width="28" alt=""/> | When authorized: “Check availability of **2 units of PRT-100** for a synthetic line inspection. Use catalog tools only; do not create or update data.” | - [ ] Verify actual tool choice, returned values and routing in source rows; prompt wording alone proves none of them. |
| 2 | <img src="./assets/icons/container-apps.svg" width="28" alt=""/> | Only if separately authorized, use the records backend MCP adapter through the APIM HTTP proxy; the preview OpenAPI-generated server instead dispatches REST. | - [ ] Verify the actual mutation and audit evidence; no writes occurred in the current review. |
| 3 | <img src="./assets/icons/policy.svg" width="28" alt=""/> | Attempt a tool that is **not** on the allow-list. | - [ ] The gateway denies the call. |

**Expected result:** actual tool operations match the deployed agent route or independently selected direct gateway. **Primary proof:** APIM backend `tool_audit` + `ApiManagementGatewayLogs` joins in 01/04, not native MCP logs, `--gateway` or a successful agent answer. Selected preview traces lack backend audit hops and remain incomplete end to end. S3 in the developer script does not execute these checks.

### S4 - Scale and posture

| Step | | Action | Validation |
|---|---|---|---|
| 1 | <img src="./assets/icons/api-management.svg" width="28" alt=""/> | Only with separate authorization, run `python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2 --probe-429`. | - [ ] Inspect any actual `429` and source logs; no observed throttle is not a pass, and status alone does not identify a token policy. |
| 2 | <img src="./assets/icons/virtual-network.svg" width="28" alt=""/> | Show the network topology and the [posture table](./10-enterprise-posture-and-scale.md#what-network_isolationtrue-deploys). | - [ ] The audience can name which hops are private and which are not yet. |

**Expected result:** limits and posture are shown with gateway-specific caveats. **Proof:** APIM logs or GenAI telemetry plus the diagrams.

### S5 - Observability

| Step | | Action | Validation |
|---|---|---|---|
| 1 | <img src="./assets/icons/log-analytics.svg" width="28" alt=""/> | Run `python scripts/run_audit_queries.py --ids demo-ids.local.json --query 01`. | - [ ] The audit rows include `gateway`, `caller` and `agent_principal`. |
| 2 | <img src="./assets/icons/application-insights.svg" width="28" alt=""/> | Re-run with `--query 04 --trace-id <id>` using the trace id from S2. | - [ ] The agent, gateway and tool spans for that trace appear together. |
| 3 | <img src="./assets/icons/workbooks.svg" width="28" alt=""/> | Open the workbook, then show the alert rule. | - [ ] The call volume, denials and token usage tiles are populated. |

**Expected result:** inspect which parts of the audit story queries 01/04 actually establish. Query 11 separates tier request telemetry, Foundry-observed tier token counts, APIM logs and agent spans. **Proof:** actual Log Analytics rows and portal views ([doc 09](./09-monitoring-and-audit.md#the-saved-queries)); S5 in the developer script is not query execution.

## Presenter notes

| | Moment | Say this | Avoid saying |
|---|---|---|---|
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> | **Gateway comparison** ![Public preview](./assets/badges/public-preview.svg) | "APIM v2 is the safe default; the AI Gateway tier is a preview side lane that we ran live for comparison." | "The preview tier has the same identity guarantees as APIM token validation." |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""/> | **Framework comparison** | "The two agents use different official host packages (`ResponsesHostServer` from Agent Framework and from `langchain-azure-ai`) but the same gateway and audit contract." | "Hosted agents require one specific SDK." |
| <img src="./assets/icons/entra-workload-id.svg" width="20" alt=""/> | **Identity** | "Runtime keys prove possession of a gateway key; they do not identify a human or agent principal." | "The key is the agent identity." |
| <img src="./assets/icons/entra-id.svg" width="20" alt=""/> | **User OBO** | "This explicit console exchange can attribute a catalog-discovery call to the signed-in user and console app; verify the same trace in query 01." | "The hosted agent delegated the user, token metadata proves downstream audit, or delegated scope enforces record authorization." |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""/> | **Monitoring** | "Tier requests are in `AppRequests`; current tier token totals are Foundry-observed and identify the gateway MI only. Query 11 keeps observation layers separate." | "Native tier token export or per-user token attribution has been proven." |
| <img src="./assets/icons/policy.svg" width="20" alt=""/> | **Security limits** | "APIM has coarse JWT validation and a global tool allowlist; public backend trust and customer authorization still need validation. The content-safety setting is wired to the preview tier, not an APIM policy." | "This proves production isolation, per-user record authorization or APIM content-safety enforcement." |

> [!CAUTION]
> **Do not show** the **Visual Workflow** canvas (retiring 2026-12-01) or the classic **Assistants API** (threads and runs). The demo is built on the current hosted-agent Responses contract; showing retiring surfaces invites the wrong follow-up questions.

<details><summary><b>Show all rehearsal commands</b></summary>

```powershell
# Dry-run the full matrix (no cloud calls)
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway apimv2 --dry-run
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway aigateway --dry-run

# One actually executed hosted-agent step (requires explicit authorization)
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent maf --gateway apimv2 --step S1

# Gateway checks
python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2 --assert-401
python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2 --probe-429

# Audit and trace queries
python scripts/run_audit_queries.py --ids demo-ids.local.json --query 01
python scripts/run_audit_queries.py --ids demo-ids.local.json --query 04 --trace-id <trace-id>
```

Step values are `S1` to `S5` and `smoke`. Defaults are `--agent maf` and `--gateway apimv2`. Dry-run prints `PLAN`; unimplemented S2-S5 report `NOT_RUN`, and an incomplete live run exits 2. Run separately listed gateway/query commands only when authorized. The expected-route flag never changes deployed agent routing.

</details>

## Live evidence

**Historical script evidence only — not validation of the new console or its auth/RBAC/deployment hooks.**

![live-tested](./assets/badges/live-tested.svg) for **both gateway lanes** and **both agents**. Run `fhagl1002` on 2026-10-02 in `eastus2`; details and defects in [04 - Testing](./04-testing.md#live-validation-2026-10-02).

[![Pass/fail matrix for walkthrough steps S1 to S5, by agent host and gateway lane](./assets/evidence/pass-fail-matrix.png)](./assets/evidence/pass-fail-matrix.png)

*Source: live run 2026-10-02, eastus2.*

| Agent (host) | Gateway | S1 | S2 | S3 | S4 | S5 |
|---|---|---|---|---|---|---|
| Microsoft Agent Framework (official `ResponsesHostServer`) | APIM Standard v2 | ✅ | ✅ | ✅ | ✅ | ✅ |
| LangGraph (official `ResponsesHostServer`) | APIM Standard v2 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Microsoft Agent Framework | AI Gateway tier ![Public preview](./assets/badges/public-preview.svg) | ✅ | ✅ | ✅ | ✅ | ✅ |
| LangGraph | AI Gateway tier ![Public preview](./assets/badges/public-preview.svg) | ✅ | ✅ | ✅ | ✅ | ✅ |

> [!TIP]
> **Presenter guidance - dated evidence, not a current acceptance claim.**
> - **Historically observed on 2026-10-02:** the script-run report recorded both agents and both gateways, missing-credential 401s and a tier throttle probe (183 of 240 calls throttled), plus audit-query rows ([09](./09-monitoring-and-audit.md#live-evidence)). Preserve that history; do not treat its all-green matrix as current browser acceptance or current script execution semantics.
> - **Scoped evidence:** the [2026-10-20 limited follow-up](./04-testing.md#limited-follow-up-2026-10-20) excludes agent prompts, writes and bursts; the subsequent [APIM-focused hosted reads](./04-testing.md#apim-focused-hosted-read-validation-2026-10-20) have their own bounded evidence. Neither establishes the new real user OBO audit claim or full human-browser acceptance. The [2026-10-19 token follow-up](./04-testing.md#ai-gateway-token-source-follow-up-2026-10-19) verifies Foundry-observed 26/21 totals across two calls, not native export or current-hour/per-user attribution.
> - **Say as design intent, not as demonstrated:** network isolation mode (what-if validated only), the `postdeploy` RBAC hook (the grant was done by hand in the run) and the other tier policy cards beyond the 429 probe.
> - If asked about the agent's identity, say the runtime principal is the hosted agent's **instance identity** ([07](./07-identity-auth-traceability.md#the-runtime-principal-is-the-instance-identity)), and that the tier lane needs it to read the runtime key from Key Vault (or `AIGW_KEY_DELIVERY=env` under a Key Vault network policy).

Next: [12 - Configuration reference](./12-configuration-reference.md) →

---

*Last updated: 2026-10-20*
