from __future__ import annotations

import base64
import json
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import ROOT, load_module


@pytest.fixture
def console():
    return load_module("demo_console", ROOT / "src" / "demo-console" / "app.py")


@pytest.fixture
def settings(console):
    return console.Settings(
        tenant="test-tenant", owner="test-owner", origin="https://console.example",
        project="https://account.services.ai.azure.com/api/projects/project",
        apim="https://apim.example", aigateway="https://tier.example", workspace="workspace",
        key_delivery="env", runtime_key="secret-test-key",
    )


class Credential:
    def __init__(self):
        self.scopes = []

    def get_token(self, scope):
        self.scopes.append(scope)
        return SimpleNamespace(token="secret-test-token")


def principal(owner="test-owner", tenant="test-tenant"):
    value = {"auth_typ": "aad", "claims": [{"typ": "oid", "val": owner}, {"typ": "tid", "val": tenant}]}
    return base64.b64encode(json.dumps(value).encode()).decode()


def headers(**overrides):
    return {
        "x-ms-client-principal": principal(), "origin": "https://console.example",
        "x-demo-console": "1", **overrides,
    }


def run(console, settings, monkeypatch, handler, **kwargs):
    original_client = httpx.Client
    monkeypatch.setattr(console.httpx, "Client", lambda **options: original_client(transport=httpx.MockTransport(handler), **options))
    runner = console.Runner(settings, Credential())
    return runner.run(console.RunInput(**kwargs)), runner


def rpc_handler(tool_result=None, tools=None):
    tools = tools or [{"name": "list_records", "inputSchema": {"type": "object"}}]
    def handler(request):
        message = json.loads(request.content)
        if message["method"] == "notifications/initialized":
            assert request.headers["mcp-session-id"] == "session"
            return httpx.Response(202)
        if message["method"] == "initialize":
            assert message["params"]["clientInfo"]["name"] == "demo-console"
            result = {"protocolVersion": "2025-06-18"}
        elif message["method"] == "tools/list":
            assert request.headers["MCP-Protocol-Version"] == "2025-06-18"
            result = {"tools": tools}
        else:
            result = tool_result or {"content": [{"type": "text", "text": "ok"}], "isError": False}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": message["id"], "result": result}, headers={"mcp-session-id": "session"})
    return handler


def test_deployer_auth_and_no_local_bypass(console, settings):
    client = TestClient(console.create_app(settings))
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/").status_code == 403
    assert client.get("/api/config", headers=headers()).status_code == 200
    assert client.get("/api/config", headers=headers(**{"x-ms-client-principal": principal(owner="other")})).status_code == 403
    assert client.get("/api/config", headers=headers(**{"x-ms-client-principal": principal(tenant="other")})).status_code == 403
    assert client.get("/api/config", headers=headers(**{"x-ms-client-principal": "malformed"})).status_code == 403
    assert TestClient(console.create_app(replace(settings, owner=""))).get("/", headers=headers()).status_code == 403


def test_container_apps_platform_principal_id(console, settings):
    client = TestClient(console.create_app(settings))
    platform_headers = {"x-ms-client-principal-id": settings.owner}
    assert client.get("/api/config", headers=platform_headers).status_code == 200
    assert client.get("/api/config", headers={**platform_headers, "x-ms-client-principal-idp": "aad"}).status_code == 200
    assert client.get("/api/config", headers={"x-ms-client-principal-id": "other-owner"}).status_code == 403
    assert client.get("/api/config", headers={**platform_headers, "x-ms-client-principal-idp": "github"}).status_code == 403
    assert client.get("/api/config", headers={"x-ms-client-principal-name": settings.owner}).status_code == 403
    assert TestClient(console.create_app(replace(settings, tenant=""))).get("/", headers=platform_headers).status_code == 403


def test_platform_headers_cannot_override_conflicting_claims(console, settings):
    client = TestClient(console.create_app(settings))
    for encoded in (principal(owner="other-owner"), principal(tenant="other-tenant"), "malformed"):
        response = client.get("/api/config", headers={
            "x-ms-client-principal-id": settings.owner, "x-ms-client-principal": encoded,
        })
        assert response.status_code == 403


@pytest.mark.parametrize("provider", ["aad", "azureActiveDirectory", "azureactivedirectory"])
@pytest.mark.parametrize("authentication_type", ["aad", "AuthenticationTypes.Federation"])
def test_entra_provider_names_are_not_claims_authentication_types(console, settings, provider, authentication_type):
    client = TestClient(console.create_app(settings))
    encoded = base64.b64encode(json.dumps({
        "auth_typ": authentication_type,
        "claims": [{"typ": "oid", "val": settings.owner}, {"typ": "tid", "val": settings.tenant}],
    }).encode()).decode()
    response = client.get("/api/config", headers={
        "x-ms-client-principal-id": settings.owner,
        "x-ms-client-principal-idp": provider,
        "x-ms-client-principal": encoded,
    })
    assert response.status_code == 200


def test_auth_denial_returns_only_categorical_diagnostics(console, settings, caplog):
    client = TestClient(console.create_app(settings))
    response = client.get("/", headers={"x-ms-client-principal-id": "private-other-owner"})
    assert response.status_code == 403
    assert response.json()["auth_reason"] == "owner_mismatch"
    assert "private-other-owner" not in response.text + caplog.text


def test_static_ui_and_public_config_never_include_secrets(console, settings):
    client = TestClient(console.create_app(settings))
    assert client.get("/", headers=headers()).status_code == 200
    response = client.get("/api/config", headers=headers())
    assert response.json()["gateways"] == ["apimv2", "aigateway"]
    assert "secret-test-key" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert client.get("/static/app.js", headers=headers()).status_code == 200


def test_csrf_and_payload_limit(console, settings):
    client = TestClient(console.create_app(settings))
    assert client.post("/api/run", headers=headers(origin="https://attacker.example"), json={"action": "model"}).status_code == 403
    assert client.post("/api/run", headers={"x-ms-client-principal": principal(), "origin": settings.origin}, json={"action": "model"}).status_code == 403
    assert client.post("/api/run", headers=headers(), content="x" * 16385).status_code == 413
    assert client.post("/api/run", headers=headers(**{"content-length": "invalid"}), content="x").status_code == 400
    assert client.post("/api/run", headers=headers(), json={"action": "model", "url": "https://attacker.example"}).status_code == 422


@pytest.mark.parametrize("kwargs", [
    {"action": "agent"}, {"action": "throttle"}, {"action": "rest-create"}, {"action": "rest-update"},
    {"action": "mcp-call", "server": "records", "tool": "create_record"},
    {"action": "mcp-call", "server": "records", "tool": "records_update_record", "gateway": "aigateway"},
])
def test_side_effects_require_server_side_confirmation(console, settings, monkeypatch, kwargs):
    def handler(_):
        pytest.fail("No upstream request is allowed without confirmation.")
    with pytest.raises(console.HTTPException) as exc:
        run(console, settings, monkeypatch, handler, **kwargs)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("status,expected", [(401, "passed"), (403, "failed"), (200, "failed"), (429, "failed")])
def test_no_credential_probe_is_exactly_401(console, settings, monkeypatch, status, expected):
    def handler(request):
        assert "authorization" not in request.headers and "api-key" not in request.headers
        return httpx.Response(status)
    result, runner = run(console, settings, monkeypatch, handler, action="unauthenticated")
    assert result["status"] == expected
    assert runner.credential.scopes == []
    assert len(result["trace_id"]) == 32


@pytest.mark.parametrize("gateway", ["apimv2", "aigateway"])
def test_model_paths_and_credential_redaction(console, settings, monkeypatch, gateway):
    def handler(request):
        expected = "/llm/openai/v1/responses" if gateway == "apimv2" else "/default/models/openai/v1/responses"
        assert request.url.path == expected
        assert request.headers.get("authorization") == ("Bearer secret-test-token" if gateway == "apimv2" else None)
        assert request.headers.get("api-key") == ("secret-test-key" if gateway == "aigateway" else None)
        return httpx.Response(200, json={"status": "completed", "output": [{"echo": "secret-test-key secret-test-token"}]})
    result, _ = run(console, settings, monkeypatch, handler, action="model", gateway=gateway)
    assert result["status"] == "passed"
    assert "secret-test-key" not in json.dumps(result)
    if gateway == "apimv2":
        assert "secret-test-token" not in json.dumps(result)


@pytest.mark.parametrize("payload", [{}, {"status": "failed"}, {"status": "incomplete"}, {"status": "completed"}, {"error": {"message": "no"}}])
def test_http_200_is_not_a_model_pass(console, settings, monkeypatch, payload):
    result, _ = run(console, settings, monkeypatch, lambda _: httpx.Response(200, json=payload), action="model")
    assert result["status"] == "failed"


def test_hosted_agent_uses_own_endpoint_not_gateway_dropdown(console, settings, monkeypatch):
    def handler(request):
        assert request.url.path.endswith("/agents/agent-langgraph/endpoint/protocols/openai/responses")
        assert request.headers["authorization"] == "Bearer secret-test-token"
        assert json.loads(request.content)["input"] == "test"
        return httpx.Response(200, json={"status": "completed", "output": []})
    result, runner = run(console, settings, monkeypatch, handler, action="agent", agent="langgraph", gateway="aigateway", prompt="test", confirmed=True)
    assert result["status"] == "passed"
    assert "configured gateway: apimv2" in result["detail"]
    assert runner.credential.scopes == ["https://ai.azure.com/.default"]


def test_mcp_session_and_application_error(console, settings, monkeypatch):
    result, _ = run(console, settings, monkeypatch, rpc_handler(tool_result={"content": [], "isError": True}), action="mcp-call", server="records", tool="list_records")
    assert result["status"] == "failed"


def test_tier_mcp_names_and_schema(console, settings, monkeypatch):
    result, _ = run(console, settings, monkeypatch, rpc_handler(tools=[{"name": "catalog_check_availability", "inputSchema": {"required": ["item_id"]}}]), action="mcp-list", gateway="aigateway")
    assert result["status"] == "passed"
    assert result["tools"][0]["inputSchema"]["required"] == ["item_id"]


def test_mcp_tool_must_be_live_advertised(console, settings, monkeypatch):
    with pytest.raises(console.HTTPException):
        run(console, settings, monkeypatch, rpc_handler(), action="mcp-call", server="records", tool="get_record")


def test_sse_multiline_and_rpc_validation(console):
    response = httpx.Response(200, headers={"content-type": "text/event-stream"}, text='event: message\ndata: {"jsonrpc":"2.0",\ndata: "id":2,"result":{"tools":[]}}\n\n')
    assert console.rpc_payload(response, 2)["result"] == {"tools": []}
    with pytest.raises(console.ProtocolFailure):
        console.rpc_payload(httpx.Response(200, json={"jsonrpc": "2.0", "id": 99, "result": {}}), 2)
    with pytest.raises(console.ProtocolFailure):
        console.decode_payload(httpx.Response(200, text="not json"))


@pytest.mark.parametrize("gateway,action", [("aigateway", "denied-tool"), ("aigateway", "rest-list")])
def test_unsupported_paths_are_unavailable(console, settings, monkeypatch, gateway, action):
    result, _ = run(console, settings, monkeypatch, lambda _: pytest.fail("Unsupported path must not make HTTP calls"), action=action, gateway=gateway)
    assert result["status"] == "unavailable"


def test_rest_facade_path_and_write(console, settings, monkeypatch):
    def handler(request):
        assert request.url.path == "/records/REC-001"
        assert request.method == "PATCH"
        assert json.loads(request.content) == {"status": "completed"}
        return httpx.Response(200, json={"id": "REC-001"})
    result, _ = run(console, settings, monkeypatch, handler, action="rest-update", record_id="REC-001", arguments={"status": "completed"}, confirmed=True)
    assert result["status"] == "passed"


def test_denial_requires_policy_specific_403(console, settings, monkeypatch):
    base = rpc_handler()
    def handler(request):
        if json.loads(request.content)["method"] == "tools/call":
            return httpx.Response(403, json={"error": {"message": "Tool is not permitted by the gateway allow-list."}})
        return base(request)
    result, _ = run(console, settings, monkeypatch, handler, action="denied-tool")
    assert result["status"] == "passed"


@pytest.mark.parametrize("code,expected", [(200, "not_run"), (429, "passed"), (401, "failed"), (503, "failed")])
def test_throttle_budget_and_verdict(console, settings, monkeypatch, code, expected):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(code, json={})
    result, _ = run(console, settings, monkeypatch, handler, action="throttle", attempts=8, confirmed=True)
    assert result["status"] == expected
    assert len(calls) == result["attempts"] == 8


def test_throttle_hard_limit(console):
    with pytest.raises(ValueError):
        console.RunInput(action="throttle", attempts=121)


@pytest.mark.parametrize("rows,expected", [([], "not_run"), ([["example"]], "passed")])
def test_audit_fixed_query_bounds_and_trace(console, settings, monkeypatch, rows, expected):
    seen = {}
    class Logs:
        def __init__(self, credential): pass
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def query_workspace(self, workspace, query, timespan):
            seen.update(workspace=workspace, query=query, timespan=timespan)
            return SimpleNamespace(status=console.LogsQueryStatus.SUCCESS, tables=[SimpleNamespace(columns=["value"], rows=rows)])
    monkeypatch.setattr(console, "LogsQueryClient", Logs)
    result = console.Runner(settings, Credential()).run(console.RunInput(action="audit", query="04", trace_id="a" * 32))
    assert result["status"] == expected
    assert 'traceId:string = "' + "a" * 32 + '"' in seen["query"]
    assert seen["query"].endswith("| take 200")
    assert seen["timespan"].total_seconds() == 3600
    with pytest.raises(ValueError):
        console.RunInput(action="audit", query="../01")


def test_infra_auth_roles_secrets_and_service_wiring():
    module = (ROOT / "infra/modules/demo-console.bicep").read_text()
    assert "defaultAuthorizationPolicy" in module and "allowedUserId" in module
    assert "clientSecretSettingName: 'entra-client-secret'" in module
    assert "maxReplicas: 1" in module
    assert "secretRef: 'aigw-runtime-key'" in module
    assert "unauthenticatedClientAction: 'RedirectToLoginPage'" in module
    assert "roleDefinitionId:" in module
    manifest = (ROOT / "azure.yaml").read_text()
    assert "demo-console:" in manifest and "./src/demo-console/Dockerfile" in manifest
    pre = (ROOT / "infra/hooks/preprovision.ps1").read_text()
    assert pre.index("Assert-AzContextMatches") < pre.index("Initialize-DemoConsoleAuth")
    assert "signed-in-user show" in (ROOT / "infra/hooks/console-auth.ps1").read_text()
    dockerignore = (ROOT / ".dockerignore").read_text()
    assert dockerignore.startswith("**\n")
    assert "!src/demo-console/**" in dockerignore
    assert "!.azure" not in dockerignore and "!demo-ids.local.json" not in dockerignore
