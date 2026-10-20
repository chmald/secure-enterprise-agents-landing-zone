# Changelog

## Unreleased

- **Consistent diagram visuals.** Restored official service icons to the architecture, walkthrough and explicit OBO lane, with neutral numbered agenda badges and matching typography/spacing. Corrected stale MI-only/Standard-tier labels, kept user-OBO proof and preview limits explicit, and added icon-coverage regression checks beside regenerated PNGs.
- **Explicit console-to-APIM user OBO.** S2 now compares anonymous, console managed identity, hosted-agent instance identity and an opt-in real user OBO path. A separate confidential sign-in client obtains a user access token for the console API; the console exchanges that access token for `Gateway.Access` and performs read-only catalog MCP discovery. Tokens and application credentials stay server-side; no hosted-agent delegation or managed-identity fallback is implied.
- **Auditable delegated subjects.** APIM accepts the exact v2 API audience and strips/stamps user name, username and scopes only from validated delegated claims. Both backends and query 01 expose the human subject separately from the calling application. The GUI can read that identity call's trace-filtered audit evidence; optional friendly fields are not substituted for the stable object ID.
- **OBO setup and safeguards.** Added owner-scoped Entra setup with persisted scopes before narrow preauthorization, ACA secret references, a form-post callback with state/PKCE/nonce/allowed-user checks, one-use/cancel/expiry controls and explicit consent/configuration failures. The legacy user-invocation sample is correctly labeled as not implementing OBO. Local and live configuration/app-only readiness checks do not constitute a completed real-user OBO grant or audit proof.
- **APIM-focused validation (2026-10-20).** Both hosted frameworks completed the approved read-only catalog scenario with verified tool inputs/results, distinct agent-instance callers and selected agent/gateway/backend trace joins. Preview is deferred; real human-browser, write and throttle sign-offs remain open. Recorded live BasicV2 versus configured StandardV2 drift without upgrading; GUI/chart labels now say APIM v2 rather than asserting a Standard SKU.
- **APIM request-count accuracy.** Queries 02/11 merge split LLM diagnostic parts by resource/correlation ID and retain nonempty model names before counting requests. The APIM validation reconciled 18 log parts to 6 model requests and matching 3,612 input / 374 output tokens; unavailable failure/latency measurements stay null. Published and verified in the console, workbook and query pack without changing preview attribution or token aggregation.
- **Session alignment (2026-10-20).** Added the eight-item discovery-to-pilot agenda to the GUI and session guide, a bundled reference architecture, a configured-workbook link and readable saved-query labels. APIM-only actions and non-demo MCP tools are visibly disabled where unsupported; controls remain locked until configuration loads. Current-state facts, pilot approvals and named owners remain to agree, not inferred.
- **Evidence and identity clarity.** Corrected reference material that overstated OBO/user attribution, backend trust, APIM content safety or current live acceptance. Rehearsal dry-runs now report `PLAN`; unimplemented S2-S5 checks report `NOT_RUN` with an incomplete-run exit code, never false `PASS`. Canonical walkthrough prompts use bounded/read-only proposals and are synchronized into both agent and tool image contexts.
- **AI Gateway tokens: verified backend source (2026-10-19).** Native tier request logs emitted zero counters despite positive response usage. Queries 02/11 and the workbook now use deduplicated Foundry `RequestResponse` counters matched to the tier's managed-identity principal ID, labeled **AI Gateway - Foundry-observed**. Native request rows retain null token counts and an explicit source gap; agent totals are never substituted. Identity binding is wired through Bicep, query pack, console and CLI, with unavailable-attribution guidance when missing.
- **REST collection routing.** `records-api` also accepts GET/POST `/records/` without redirects (hidden from OpenAPI), preserving canonical `/records` routes and the console's no-redirect credential boundary. Existing environments need `azd provision` then `azd deploy records-api demo-console` so both fixes ship together.
- **Azure-hosted demo console.** One FastAPI + plain HTML/CSS/JS Container App, `ca-demo-console`, in the existing ACA environment; `azd` service `demo-console` builds remotely with repository-root Docker context. Single-tenant Easy Auth allowlists the deployer; the backend verifies ACA's trusted principal ID and rejects conflicting owner/tenant claims when supplied. Managed identity performs downstream calls, never browser tokens or OBO. Deployment and limited live checks are documented separately from the still-pending complete browser acceptance matrix.
- **Console lifecycle and safeguards.** Hooks verify tenant/subscription, resolve a signed-in human deployer, create a separate single-tenant Entra app/credential and configure its redirect. Console auth inputs fail closed when blank; the secret stays in gitignored azd state and an ACA secret. Rotation, manual Entra cleanup after `azd down`, RBAC scopes and isolated-browser access are documented.
- **Browser S1-S5 and visuals.** Agent prompts, direct model/MCP/REST checks, bounded throttle bursts, and saved KQL 01-11 expose detailed responses with `passed` / `failed` / `unavailable` / `not_run`. Every agent submission, direct write, and burst requires confirmation. APIM-only denied-tool and REST checks are not presented as tier parity; trace IDs and successful responses are not proof of tool choice/propagation. Updated architecture and walkthrough editable diagrams and PNGs; earlier live evidence is explicitly historical, not console validation.
- **Console authentication repairs.** Replaced a Windows `az.cmd`-unsafe `length(@)` lookup with `[0].id`; enabled ID-token issuance for Easy Auth's callback flow; accepted ACA scalar identity headers and Entra provider aliases without confusing `auth_typ` with the provider. Restricted Easy Auth's allowed browser origin to the console HTTPS URL while retaining the backend's origin/custom-header checks and deployer allowlist.
- **Demo-only tier key delivery.** `AIGW_KEY_DELIVERY=env` delivers the tier key through a secure Bicep output and ACA secret reference, never browser configuration. This addresses a console outside a private vault's network boundary; it does not enable Key Vault public access. Default `keyvault` delivery still requires RBAC and network reachability. APIM's managed-identity bearer path is unchanged.
- **Workbook coverage and schema.** Expanded to 17 query panels in seven labeled sections, bound to the 11 maintained saved KQL files. Corrected APIM latency/error fields and message-column compatibility, optional trace input, tool-audit correlation links, recorded identity labels, platform audit and telemetry coverage. Trace controls filter only the timeline and hosted-agent content; the time range applies throughout.
- **Token chart rendering and time range.** Restored separate gateway/agent input/output series. Explicit source filters run before joins/aggregation; chart buckets follow the selected start/end/grain with zero-filled gaps for observed series. Workbook datetime expressions are used directly, not double-wrapped. Paired `mv-expand` returns scalar datetime/long/string chart columns instead of JSON arrays; the 200-series cap precedes expansion so all 224 agent points in a seven-day/three-hour view survive. Detail-table limits remain unchanged.
- **Validation boundaries and runbooks.** Added the [2026-10-16 follow-up](./docs/04-testing.md#live-follow-up-2026-10-16), browser acceptance and workbook visual checks, symptom-specific fixes and workbook-only upgrade guidance. Console health/access rejection, in-container tier discovery/read calls, and persisted workbook query schemas/totals were checked live. The full browser S1-S5 matrix and the final refreshed portal rendering are not claimed as completed.

- Docs: rewrote for external audiences; removed internal terminology. Policy-specific references now describe a generic organization policy that disables Key Vault public network access (docs, README, `postprovision`/`postdeploy-agents` hook messages); audience lines name platform engineers and developers; demo and walkthrough wording no longer assumes a customer session; the gateway-modes diagram reads "Recommendation: default baseline" (PNG re-exported); `lint_doc_visuals.py` docstrings use neutral wording and a `<repo-root>` example. `tests/test_reusability_guards.py` gains `test_no_internal_terminology` over every tracked text file.

## 1.2.0 - 2026-10-02

Official agent hosts, AI Gateway tier proven live, and isolation mode now creates its private endpoints.

### What changed

- **Official hosts, no fallback.** `agent-maf` runs on `agent_framework_foundry_hosting.ResponsesHostServer` and `agent-langgraph` on `langchain_azure_ai.agents.hosting.ResponsesHostServer`; both serve `responses` 2.0.0 on port 8088. The hand-written FastAPI fallback was removed. Agent requirements install with `--pre`; the Dockerfile gained `ARG PIP_INDEX_URL` and `chown app:app /app` (otherwise `PermissionError: /app/.agentserver`).
- **Runtime configuration.** Hosted agents read `HOSTED_DEFAULT_GATEWAY`, `HOSTED_PROTOCOL` and `HOSTED_RUNTIME` (the unprefixed `AGENT_*` names are a local-run fallback) and the platform-injected `APPLICATIONINSIGHTS_CONNECTION_STRING`, `FOUNDRY_AGENT_INSTANCE_CLIENT_ID` and `FOUNDRY_HOSTING_ENVIRONMENT`.
- **AI Gateway tier is live.** The tier is `Microsoft.ApiManagement/service@2025-09-01-preview` with sku `AIGateway` (it needs the `AIGatewayPreview` feature registered). The 1.1.0 `Microsoft.ApiManagement/aigateways` / `2026-05-01-preview` shape never worked and was removed. Model alias name must equal the request `model` (`chat`), the provider `modelName` must equal the Foundry deployment name, and the OpenAPI tool server needs an absolute `servers[0].url`.
- **Identity finding.** A hosted agent's effective runtime principal is its **instance identity** (`azd ai agent show <agent> --output json` -> `instance_identity.principal_id`), distinct from the blueprint and the Foundry project identity. It only exists after deploy, so Bicep cannot grant it **Key Vault Secrets User**.
- **Key delivery.** New `AIGW_KEY_DELIVERY` (`keyvault` default, `env` opt-in) and a `postdeploy` hook (`infra/hooks/postdeploy-agents.ps1`) that grants the instance identity Key Vault Secrets User. Under a Key Vault network policy (`ForbiddenByConnection`), isolation mode is the proper fix and `env` delivery the demo-only compromise. The hook is covered by offline tests but was **not live-verified** (the grant was made by hand).
- **Isolation mode creates private endpoints and DNS.** Nine private DNS zones and eight private endpoints (Foundry, Key Vault, Container Registry, APIM v2, AI Gateway tier, Cosmos DB, Storage, AI Search), `snet-aigw`, `AIGW_SUBNET_PREFIX` and `AIGW_INBOUND_PRIVATE_ENDPOINT`. Validated with `az bicep build` and `what-if` (127 resources, no errors); **not deployed live**.
- **Telemetry fixes.** The tier writes LLM and MCP calls to Application Insights `AppRequests`, not `ApiManagementGatewayLlmLog`. Saved queries 02, 04, 09 and 11 were rewritten; `run_audit_queries.py` substitutes `--trace-id`.
- **Docs and visuals.** Seven new diagrams (service catalog, prerequisites map, manual deployment steps, testing matrix, troubleshooting decision tree, gateway identity comparison, scale limits), badges for every status table, a doc-visuals linter (`scripts/lint_doc_visuals.py`) and test (`tests/test_doc_visuals.py`).

### Live validation (2026-10-02)

Disposable `eastus2` deployment `fhagl1002`. Evidence and charts: [`docs/04-testing.md`](./docs/04-testing.md#live-validation-2026-10-02), [`docs/09-monitoring-and-audit.md`](./docs/09-monitoring-and-audit.md#live-evidence), [`docs/11-demo-walkthrough.md`](./docs/11-demo-walkthrough.md#live-evidence); raw run in `docs/assets/evidence/live-run-2026-10-02.json`.

- **Matrix:** both agents (MAF, LangGraph) x both gateways (APIM Standard v2, AI Gateway tier) passed S1-S5. Gateway validation: 401 without credential, 200 with, MCP `initialize`/`tools/list`/`tools/call` (`catalog_list_items`, `records_list_records`), and the 429 probe (183 of 240 requests throttled on the tier).
- **Saved queries (rows):** 01=75, 02=5, 03=70, 04=104, 05=67, 06=100, 07=0, 08=0, 09=0, 10=942, 11=30. Queries 07, 08 and 09 are empty by environment, not defects.
- **Durations:** provision #2 4m45s and #3 3m04s (#1 failed on the Container Apps registry pull identity); catalog deploy 1m24s, records 1m19s; MAF v1/v2/v3 2m48s / 1m43s / 1m48s; LangGraph 2m16s / 2m07s / 1m59s; APIM v2 walkthrough 32s.
- **Teardown:** `azd down --purge --force` took 36m33s; the Cognitive Services account was purged manually and the Entra app deleted by hand.

| # | Defect | Fix |
|---|---|---|
| 1 | Container Apps user-assigned identity could not pull from the registry | Grant `AcrPull` to the ACA identity |
| 2 | Missing outputs `AZURE_AI_PROJECT_ID`, `AZURE_AI_PROJECT_ENDPOINT`, `AIGW_RUNTIME_KEY_SECRET_NAME` | Added to `main.bicep` |
| 3 | Gateway provider `modelName` did not match the Foundry deployment name | Provider `modelName` = deployment name |
| 4 | `validate_gateway` used one tool name set and a serial 429 probe | Per-gateway tool names; concurrent probe |
| 5 | `postprovision` strict-mode and `listSecrets` parsing errors | Hook fixed |
| 6 | Hosted agent could not read Key Vault under policy | `AIGW_KEY_DELIVERY` and env fallback |
| 7 | Query 02 returned blank agent and user | Union of LLM log, tier `AppRequests` and agent spans |
| 8 | Query 11 returned placeholder noise | Rewritten over `AppRequests` and the MCP log |
| 9 | Query 04 returned thousands of rows (trace parameter never substituted) | `--trace-id` substitution |
| 10 | Query 09 failed: `ErrorMessage` does not exist | Use `LastErrorMessage` |
| 11 | Evidence renderer captions and labels | Updated; matrix labels show host type |

### Remaining gaps

- Network isolation mode is not deployed live; the hosted-agent endpoint is not private via azd, and APIM and the tier stay public until a manual lockdown.
- The `postdeploy` RBAC hook and the AI Gateway tier private endpoint are not live-verified.
- Only the 429 policy card was exercised on the tier (token limit, content safety and IP filter are deployed but untested).

### History

- The 1.1.0 `DD_*` telemetry variables and the `FHAGL_USE_FASTAPI_FALLBACK` switch were removed in this release.

## 1.1.0 - 2026-10-01

Dual-gateway and dual-framework update. Superseded in part by 1.2.0 (see corrections below).

### What changed

- Added `AI_GATEWAY_MODE=both` so APIM Standard v2 and AI Gateway tier preview can be deployed and tested side by side.
- Documented AI Gateway tier preview boundaries: East US 2 / Sweden Central, runtime `api-key` auth, gateway-scoped runtime keys, no SLA, pricing TBA, and standalone portal `ai.gateway.azure.com`. (The 1.1.0 management API shape was wrong; see 1.2.0.)
- Replaced the legacy single `src/hosted-agent` narrative with two hosted-agent implementations: `src/agents/maf` and `src/agents/langgraph`.
- Updated deployment and testing instructions for `AGENT_DEFAULT_GATEWAY=aigateway` plus `azd deploy agent-maf agent-langgraph` second pass.
- Added configuration coverage for all new variables, outputs, demo ID keys, runtime env vars, and script surfaces.
- Updated diagrams for architecture, gateway modes, identity token flow, azd deployment flow, configuration flow, and agent-framework comparison.
- Added query 11 for AI Gateway tier telemetry comparison.

### Live validation (2026-10-01)

Disposable `eastus2` deployment, torn down afterwards. Raw run: `docs/assets/evidence/live-run-2026-10-01.json`.

- **Live-tested (APIM Standard v2):** `azd up`, gateway validation, and walkthrough S1-S5 for both agents passed.
- **AI Gateway tier not deployable in 1.1.0:** the `aigateways` resource type failed with `InvalidResourceType`. Fixed in 1.2.0 by using the `service` resource with sku `AIGateway`.
- **17 defects found and fixed live** (Bicep ordering, RBAC, unsupported Standard v2 policy, MCP shape, container build context, reserved hosted-agent env names, schema drift in query 06 and others). Added `scripts/render_evidence.py` plus `docs/assets/evidence/` charts, and `matplotlib` to `scripts/requirements.txt`.
- **Teardown caveat:** `azd down --purge --force` left API Management behind; an explicit `az group delete` was required.

## 1.0.0 - 2026-09-30

Initial reusable demo pattern for Foundry hosted agents behind an APIM AI Gateway landing zone.

### Shipped

- Core document set: README plus `docs/00` through `docs/12`.
- Distribution guardrails: `.gitignore` and `demo-ids.template.json`.
- Locked decisions D1-D10, gateway-mode comparison, tenant-explicit quick start, manual deployment path, testing/troubleshooting runbooks, and diagrams.

---

*Last updated: 2026-10-16*
