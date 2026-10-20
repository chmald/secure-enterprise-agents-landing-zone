"use strict";
const $ = id => document.getElementById(id);
let tools = [];
let busy = false;
let ready = false;
let oboAvailable = false;
let oboInProgress = false;
let identityCancelled = false;
let identityTrace = "";

function showStep(step) {
  for (const id of ["S1", "S2", "S3", "S4", "S5"]) $(id).hidden = id !== step;
  document.querySelectorAll("[data-step]").forEach(button => button.setAttribute("aria-current", button.dataset.step === step ? "step" : "false"));
}
document.querySelectorAll("[data-step]").forEach(button => button.addEventListener("click", () => showStep(button.dataset.step)));
document.querySelectorAll("[data-agenda-step]").forEach(button => button.addEventListener("click", () => showStep(button.dataset.agendaStep)));

function updateControls() {
  const tier = $("gateway").value === "aigateway";
  $("server").querySelector('option[value="records"]').textContent = tier ? "Records / OpenAPI-generated MCP" : "Records / backend MCP adapter";
  $("tool-path").textContent = tier
    ? "Preview route: remote catalog MCP; the gateway's OpenAPI-generated records tools call the sample REST backend."
    : "APIM route: HTTP policies proxy the sample catalog and records MCP adapters. Records MCP and REST share business functions; this is not an APIM-generated MCP server.";
  document.querySelectorAll("button, select, textarea, input").forEach(element => {
    const unsupported = element.hasAttribute("data-apim-only") && $("gateway").value !== "apimv2";
    element.disabled = busy || (!ready && element.matches("[data-action], [data-identity]")) || unsupported
      || (element.id === "obo-call" && !oboAvailable)
      || (element.id === "identity-audit" && !identityTrace);
    if (element.hasAttribute("data-apim-only")) element.title = unsupported ? "This operation requires the APIM v2 direct gateway." : "";
  });
  $("cancel-obo").hidden = !oboInProgress;
  $("cancel-obo").disabled = !oboInProgress || identityCancelled;
}

function displayResult(result, action, label) {
  $("status").textContent = result.status;
  $("status").dataset.status = result.status;
  $("summary").textContent = result.detail || `${action}: ${result.status}`;
  $("result").textContent = JSON.stringify(result, null, 2);
  if (result.trace_id && action !== "audit" && action !== "identity-audit") $("trace-id").value = result.trace_id;
  const entry = document.createElement("li");
  entry.textContent = `${new Date().toLocaleTimeString()} | ${action} | ${label} | ${result.status} | ${result.trace_id || "no downstream trace"}`;
  $("history").prepend(entry);
}

function displayIdentity(result) {
  identityTrace = result.status === "passed" ? result.trace_id : "";
  $("identity-summary").textContent = result.detail;
  $("identity-fields").replaceChildren();
  const identity = result.identity;
  if (!identity) return;
  const values = {
    "Call path": result.identity_mode,
    "Principal object ID": identity.principal_object_id,
    "Calling application ID": identity.calling_application_id,
    "User object ID": identity.user_object_id || "None (application-only)",
    "User display name": identity.user_name || "Not reported",
    "User username": identity.user_username || "Not reported",
    "Token audience": identity.audience,
    "Delegated scopes": identity.delegated_scopes.join(", ") || "None",
    "Application roles": identity.application_roles.join(", ") || "None reported",
    "Trace ID": result.trace_id,
  };
  for (const [name, value] of Object.entries(values)) {
    const term = document.createElement("dt"), description = document.createElement("dd");
    term.textContent = name; description.textContent = value;
    $("identity-fields").append(term, description);
  }
}

async function identityRequest(path, method = "POST") {
  const response = await fetch(path, {
    method, redirect: "error",
    ...(method === "POST" ? { headers: { "Content-Type": "application/json", "X-Demo-Console": "1" }, body: "{}" } : {}),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "Identity request failed.");
  return result;
}

async function runIdentity(mode) {
  if (busy) return;
  if (!ready || $("gateway").value !== "apimv2") throw new Error("Load configuration and select APIM for identity comparison.");
  const popup = mode === "obo" ? window.open("about:blank", "_blank", "width=650,height=800") : null;
  if (mode === "obo" && !popup) throw new Error("Allow the Entra sign-in popup, then try again. No request was sent.");
  busy = true; oboInProgress = mode === "obo"; identityCancelled = false; identityTrace = "";
  updateControls();
  document.querySelector(".results").setAttribute("aria-busy", "true");
  $("identity-fields").replaceChildren();
  $("identity-summary").textContent = mode === "obo" ? "Complete sign-in as the deployer in the Entra popup. No application-identity fallback is used." : "Calling APIM as the console managed identity.";
  $("summary").textContent = $("identity-summary").textContent;
  $("status").textContent = "running"; $("status").dataset.status = "running";
  try {
    let result;
    if (mode === "obo") {
      const start = await identityRequest("/api/identity/obo/start");
      popup.location.replace(start.authorization_url);
      const deadline = Date.now() + 600000;
      while (Date.now() < deadline) {
        if (identityCancelled) throw new Error("Pending sign-in cancelled. A call already started cannot be rolled back.");
        result = await identityRequest("/api/identity/obo/result", "GET");
        if (result.status !== "not_run") break;
        await new Promise(resolve => setTimeout(resolve, 1500));
      }
      if (!result || result.status === "not_run") throw new Error("Sign-in expired. Start a new OBO sign-in; no identity fallback was used.");
    } else {
      result = await identityRequest("/api/identity/managed");
    }
    displayResult(result, "identity", result.identity_mode);
    displayIdentity(result);
  } finally {
    if (popup && !popup.closed) popup.close();
    busy = false; oboInProgress = false;
    document.querySelector(".results").setAttribute("aria-busy", "false");
    updateControls();
  }
}

document.querySelectorAll("[data-identity]").forEach(button => button.addEventListener("click", () => runIdentity(button.dataset.identity).catch(reportError)));
$("cancel-obo").addEventListener("click", async () => {
  identityCancelled = true;
  updateControls();
  try { await identityRequest("/api/identity/obo/cancel"); }
  catch (error) { reportError(error); }
});

function resetTools() {
  tools = [];
  $("tool").replaceChildren(new Option("Discover tools first", ""));
  $("schema").textContent = "No tools discovered for this server and gateway.";
  $("arguments").value = "{}";
  $("write-confirm").checked = false;
}
$("gateway").addEventListener("change", () => {
  resetTools();
  $("throttle-confirm").checked = false;
  updateControls();
});
$("server").addEventListener("change", resetTools);
$("agent").addEventListener("change", () => { $("agent-confirm").checked = false; });
$("record-id").addEventListener("input", () => { $("write-confirm").checked = false; });
$("tool").addEventListener("change", () => {
  const tool = tools.find(item => item.name === $("tool").value);
  const schema = tool?.inputSchema || {};
  $("schema").textContent = JSON.stringify(schema, null, 2);
  const sample = {};
  for (const [name, property] of Object.entries(schema.properties || {})) {
    if (!(schema.required || []).includes(name)) continue;
    sample[name] = property.default ?? property.enum?.[0] ?? ({ array: [], object: {}, integer: 1, number: 1, boolean: false }[property.type] ?? "");
  }
  $("arguments").value = JSON.stringify(sample, null, 2);
  $("write-confirm").checked = false;
});
$("arguments").addEventListener("input", () => { $("write-confirm").checked = false; });
$("prompt").addEventListener("input", () => { $("agent-confirm").checked = false; });
$("prompt-preset").addEventListener("change", () => {
  if ($("prompt-preset").value) $("prompt").value = $("prompt-preset").value;
  $("agent-confirm").checked = false;
});
$("attempts").addEventListener("input", () => { $("throttle-confirm").checked = false; });

async function run(action) {
  if (busy) return;
  if (!ready) throw new Error("Deployment configuration has not loaded. No request was sent.");
  const data = { action: action === "identity-audit" ? "audit" : action, gateway: $("gateway").value, agent: $("agent").value, server: $("server").value };
  if (action === "identity-audit") {
    if (!identityTrace) throw new Error("Run an identity probe before reading its audit.");
    data.query = "01";
    data.trace_id = identityTrace;
  }
  if (action === "agent") {
    data.prompt = $("prompt").value;
    data.confirmed = $("agent-confirm").checked;
  }
  if (action === "mcp-call" || action === "rest-create" || action === "rest-update") {
    data.tool = $("tool").value;
    data.arguments = JSON.parse($("arguments").value);
    if (!data.arguments || Array.isArray(data.arguments) || typeof data.arguments !== "object") throw new Error("Arguments must be a JSON object.");
    data.confirmed = $("write-confirm").checked;
  }
  if (action === "mcp-call" && !data.tool) throw new Error("Discover and select a live tool first.");
  if (action === "rest-get" || action === "rest-update") data.record_id = $("record-id").value;
  if (action === "audit") {
    data.query = $("query").value;
    data.trace_id = $("trace-id").value.trim();
  }
  if (action === "throttle") {
    data.attempts = Number($("attempts").value);
    data.confirmed = $("throttle-confirm").checked;
  }
  busy = true;
  updateControls();
  document.querySelector(".results").setAttribute("aria-busy", "true");
  $("status").textContent = "running";
  $("status").dataset.status = "running";
  $("summary").textContent = "Waiting for the live Azure response. No automatic retries.";
  try {
    const response = await fetch("/api/run", {
      method: "POST", headers: { "Content-Type": "application/json", "X-Demo-Console": "1" },
      body: JSON.stringify(data), redirect: "error",
    });
    const result = await response.json();
    if (!response.ok) throw new Error(JSON.stringify(result.detail || result));
    displayResult(result, action, action === "agent" ? data.agent : data.gateway);
    if (action === "identity-audit") $("identity-audit-result").textContent = JSON.stringify(result.tables || result, null, 2);
    if (action === "mcp-list" && result.status === "passed") {
      tools = result.tools;
      $("tool").replaceChildren(new Option("Select a discovered tool", ""), ...tools.map(tool => {
        const option = new Option(tool.console_supported === false ? `${tool.name} (not demo-enabled)` : tool.name, tool.name);
        option.disabled = tool.console_supported === false;
        return option;
      }));
    }
  } finally {
    busy = false;
    updateControls();
    document.querySelector(".results").setAttribute("aria-busy", "false");
    for (const id of ["agent-confirm", "write-confirm", "throttle-confirm"]) $(id).checked = false;
  }
}
function reportError(error) {
  $("status").textContent = "failed";
  $("status").dataset.status = "failed";
  $("summary").textContent = error.message;
  $("result").textContent = "Request did not complete successfully. Do not assume a record write was rolled back; inspect records before retrying.";
}
document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => run(button.dataset.action).catch(reportError)));

async function initialize() {
  const response = await fetch("/api/config", { redirect: "error" });
  if (!response.ok) throw new Error("Cannot load deployment configuration. Check Entra sign-in and deployer access.");
  const config = await response.json();
  oboAvailable = config.obo.available;
  $("obo-availability").textContent = config.obo.detail;
  $("profile").textContent = config.profile;
  $("prompt-preset").replaceChildren(new Option("Custom prompt", ""), ...config.walkthrough
    .filter(step => step.step === "S1" || step.step === "S3")
    .map(step => new Option(`${step.step} / ${step.segment}`, step.prompt)));
  $("agent-route").textContent = `Hosted gateway snapshot: ${config.agent_gateway} (last provisioning, not live discovery). Verify the deployed route after agent-only changes. Direct selection does not switch hosted agents.`;
  const names = { apimv2: "APIM v2 (Entra)", aigateway: "AI Gateway tier (preview)" };
  $("gateway").replaceChildren(...config.gateways.map(name => new Option(names[name], name)));
  if (!config.gateways.length) throw new Error("No gateways configured in this deployment.");
  if (!config.queries.length) throw new Error("No saved KQL queries are bundled in this deployment.");
  $("query").replaceChildren(...config.queries.map(query => new Option(query.label, query.id)));
  $("scenario").textContent = `Representative prompt: ${config.walkthrough.find(step => step.step === "S3")?.prompt || "Select a domain prompt in S1."}`;
  $("connection-status").textContent = `Configured only: ${config.gateways.length} gateway(s); Foundry project ${config.connections.foundry_project ? "configured" : "missing"}; audit workspace ${config.connections.audit_workspace ? "configured" : "missing"}; ${config.queries.length} bundled queries. Not a health or authorization check.`;
  if (config.workbook_url) {
    $("workbook-link").href = config.workbook_url;
    $("workbook-link").hidden = false;
    $("workbook-state").hidden = true;
  } else {
    $("workbook-state").textContent = "Workbook link is not configured (WORKBOOK_ID); saved queries below remain available.";
  }
  ready = true;
  updateControls();
  showStep("S1");
}
$("architecture").addEventListener("error", () => {
  $("architecture").hidden = true;
  $("reference-status").textContent = "Reference image unavailable. Check the console image bundle; do not treat this as an architecture validation.";
});
updateControls();
initialize().catch(reportError);
