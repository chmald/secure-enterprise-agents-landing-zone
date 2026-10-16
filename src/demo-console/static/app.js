"use strict";
const $ = id => document.getElementById(id);
let tools = [];
let busy = false;

function showStep(step) {
  for (const id of ["S1", "S2", "S3", "S4", "S5"]) $(id).hidden = id !== step;
  document.querySelectorAll("[data-step]").forEach(button => button.setAttribute("aria-current", button.dataset.step === step ? "step" : "false"));
}
document.querySelectorAll("[data-step]").forEach(button => button.addEventListener("click", () => showStep(button.dataset.step)));

function resetTools() {
  tools = [];
  $("tool").replaceChildren(new Option("Discover tools first", ""));
  $("schema").textContent = "No tools discovered for this server and gateway.";
  $("arguments").value = "{}";
  $("write-confirm").checked = false;
}
$("gateway").addEventListener("change", resetTools);
$("server").addEventListener("change", resetTools);
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
  const data = { action, gateway: $("gateway").value, agent: $("agent").value, server: $("server").value };
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
  document.querySelectorAll("button, select, textarea, input").forEach(element => { element.disabled = true; });
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
    $("status").textContent = result.status;
    $("status").dataset.status = result.status;
    $("summary").textContent = result.detail || `${action}: ${result.status}`;
    $("result").textContent = JSON.stringify(result, null, 2);
    if (result.trace_id && action !== "audit") $("trace-id").value = result.trace_id;
    if (action === "mcp-list" && result.status === "passed") {
      tools = result.tools;
      $("tool").replaceChildren(new Option("Select a discovered tool", ""), ...tools.map(tool => new Option(tool.name, tool.name)));
    }
    const entry = document.createElement("li");
    entry.textContent = `${new Date().toLocaleTimeString()} | ${action} | ${action === "agent" ? data.agent : data.gateway} | ${result.status} | ${result.trace_id}`;
    $("history").prepend(entry);
  } finally {
    busy = false;
    document.querySelectorAll("button, select, textarea, input").forEach(element => { element.disabled = false; });
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
  $("profile").textContent = config.profile;
  $("prompt-preset").replaceChildren(new Option("Custom prompt", ""), ...config.walkthrough
    .filter(step => step.step === "S1" || step.step === "S3")
    .map(step => new Option(`${step.step} / ${step.segment}`, step.prompt)));
  $("agent-route").textContent = `Hosted gateway snapshot: ${config.agent_gateway} (last provisioning). Re-provision to align after agent-only gateway changes. Direct selection does not switch hosted agents.`;
  const names = { apimv2: "APIM Standard v2", aigateway: "AI Gateway tier (preview)" };
  $("gateway").replaceChildren(...config.gateways.map(name => new Option(names[name], name)));
  if (!config.gateways.length) throw new Error("No gateways configured in this deployment.");
  showStep("S1");
}
initialize().catch(reportError);
