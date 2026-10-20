from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, quote

import httpx
from azure.core.exceptions import AzureError
from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from identity import COOKIE_NAME, FLOW_TTL, RESULT_TTL, IdentityError, UserObo, token_identity

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = Path(__file__).parent / "static"
LOG = logging.getLogger("demo_console")


class OAuthCallbackAccessFilter(logging.Filter):
    demo_oauth_filter = True

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) >= 3 and isinstance(record.args[2], str):
            if "/api/identity/obo/callback?" in record.args[2]:
                args = list(record.args)
                args[2] = args[2].split("?", 1)[0]
                record.args = tuple(args)
        return True


access_log = logging.getLogger("uvicorn.access")
if not any(getattr(value, "demo_oauth_filter", False) for value in access_log.filters):
    access_log.addFilter(OAuthCallbackAccessFilter())

TOOLS = {
    "catalog": {"list_items", "search_items", "get_item", "check_availability", "check_availability_batch"},
    "records": {"list_records", "get_record", "create_record", "update_record"},
}
Action = Literal[
    "agent", "model", "unauthenticated", "mcp-list", "mcp-call", "denied-tool",
    "rest-list", "rest-get", "rest-create", "rest-update", "throttle", "audit",
]


class RunInput(BaseModel):
    action: Action
    gateway: Literal["apimv2", "aigateway"] = "apimv2"
    agent: Literal["maf", "langgraph"] = "maf"
    server: Literal["catalog", "records"] = "catalog"
    tool: str = Field(default="", max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)
    prompt: str = Field(default="Return 'ready' only.", min_length=1, max_length=4000)
    record_id: str = Field(default="", max_length=100, pattern=r"^[A-Za-z0-9_-]*$")
    query: str = Field(default="01", pattern=r"^(0[1-9]|1[01])$")
    trace_id: str = Field(default="", pattern=r"^([0-9a-f]{32})?$")
    attempts: int = Field(default=24, ge=1, le=120)
    confirmed: bool = False
    model_config = {"extra": "forbid"}


@dataclass(frozen=True)
class Settings:
    tenant: str
    owner: str
    origin: str
    profile: str = "manufacturing-field-ops"
    agent_gateway: str = "apimv2"
    project: str = ""
    apim: str = ""
    aigateway: str = ""
    aigw_principal_id: str = ""
    llm_path: str = "llm"
    model: str = "chat"
    workspace: str = ""
    workbook_id: str = ""
    vault: str = ""
    secret_name: str = "aigw-runtime-key"
    key_delivery: str = "keyvault"
    runtime_key: str = ""
    enable_obo: bool = False
    console_client_id: str = ""
    console_client_secret: str = field(default="", repr=False)
    obo_client_id: str = ""
    obo_client_secret: str = field(default="", repr=False)
    gateway_client_id: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            tenant=os.environ.get("AZURE_TENANT_ID", ""),
            owner=os.environ.get("DEMO_CONSOLE_ALLOWED_USER_ID", ""),
            origin=os.environ.get("DEMO_CONSOLE_URL", "").rstrip("/"),
            profile=os.environ.get("DOMAIN_PROFILE", "manufacturing-field-ops"),
            agent_gateway=os.environ.get("HOSTED_DEFAULT_GATEWAY", "apimv2"),
            project=os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "").rstrip("/"),
            apim=os.environ.get("APIM_GATEWAY_URL", "").rstrip("/") if os.environ.get("AI_GATEWAY_MODE", "apimv2") != "aigateway" else "",
            aigateway=os.environ.get("AIGW_GATEWAY_URL", "").rstrip("/"),
            aigw_principal_id=os.environ.get("AIGW_PRINCIPAL_ID", ""),
            llm_path=os.environ.get("LLM_API_PATH", "llm").strip("/"),
            model=os.environ.get("MODEL_DEPLOYMENT_NAME", "chat"),
            workspace=os.environ.get("LOG_ANALYTICS_CUSTOMER_ID", ""),
            workbook_id=os.environ.get("WORKBOOK_ID", ""),
            vault=os.environ.get("KEY_VAULT_URI", ""),
            secret_name=os.environ.get("AIGW_RUNTIME_KEY_SECRET_NAME", "aigw-runtime-key"),
            key_delivery=os.environ.get("AIGW_KEY_DELIVERY", "keyvault"),
            runtime_key=os.environ.get("AIGW_RUNTIME_KEY", ""),
            enable_obo=os.environ.get("ENABLE_DEMO_OBO", "false").lower() == "true",
            console_client_id=os.environ.get("DEMO_CONSOLE_CLIENT_ID", ""),
            console_client_secret=os.environ.get("DEMO_CONSOLE_CLIENT_SECRET", ""),
            obo_client_id=os.environ.get("DEMO_OBO_CLIENT_ID", ""),
            obo_client_secret=os.environ.get("DEMO_OBO_CLIENT_SECRET", ""),
            gateway_client_id=os.environ.get("GATEWAY_APP_CLIENT_ID", ""),
        )


class Unavailable(Exception):
    pass


class ProtocolFailure(Exception):
    pass


def audit_query_directory() -> Path:
    return Path("/queries") if Path("/queries").exists() else ROOT / "infra" / "monitoring" / "queries"


def canonical_tool_name(gateway: str, server: str, name: str) -> str:
    return name.removeprefix(f"{server}_") if gateway == "aigateway" else name


def decode_payload(response: httpx.Response, request_id: int | None = None) -> Any:
    if "text/event-stream" not in response.headers.get("content-type", ""):
        try:
            return response.json()
        except ValueError:
            raise ProtocolFailure("Upstream returned a non-JSON response.") from None
    # MCP Streamable HTTP may return JSON-RPC inside SSE, including multiline data.
    for event in re.split(r"\r?\n\r?\n", response.text):
        data = "\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith("data:"))
        if not data or data == "[DONE]":
            continue
        try:
            value = json.loads(data)
        except ValueError:
            raise ProtocolFailure("Upstream returned invalid SSE JSON.") from None
        if isinstance(value, dict) and (request_id is None or value.get("id") == request_id):
            return value
    raise ProtocolFailure("No matching JSON-RPC response in upstream SSE.")


def successful(response: httpx.Response, payload: Any) -> bool:
    if not response.is_success or not isinstance(payload, dict):
        return False
    result = payload.get("result", {})
    return not (
        payload.get("error")
        or payload.get("status") in {"failed", "incomplete", "cancelled", "queued", "in_progress"}
        or (isinstance(result, dict) and result.get("isError"))
    )


def completed_response(response: httpx.Response, payload: Any) -> bool:
    return successful(response, payload) and payload.get("status") == "completed" and isinstance(payload.get("output"), list)


def rpc_payload(response: httpx.Response, request_id: int) -> dict[str, Any]:
    payload = decode_payload(response, request_id)
    if (
        not successful(response, payload) or payload.get("jsonrpc") != "2.0"
        or payload.get("id") != request_id or not isinstance(payload.get("result"), dict)
    ):
        raise ProtocolFailure(f"Invalid or failed MCP JSON-RPC response (HTTP {response.status_code}).")
    return payload


class Runner:
    def __init__(self, settings: Settings, credential: Any = None) -> None:
        self.settings = settings
        self.credential = credential or ManagedIdentityCredential()
        self.throttle_lock = threading.Lock()

    def identity_probe(self, delegated_token: str | None = None) -> dict[str, Any]:
        tp = f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"
        mode = "user_obo" if delegated_token is not None else "console_managed_identity"
        secrets = [delegated_token] if delegated_token else []
        try:
            if not self.settings.apim:
                raise Unavailable("Identity comparison requires the APIM route.")
            headers = {"traceparent": tp, "Content-Type": "application/json"}
            headers.update({"Authorization": f"Bearer {delegated_token}"} if delegated_token is not None else self.headers("apimv2", secrets))
            token = headers["Authorization"].removeprefix("Bearer ")
            identity = token_identity(token)
            if delegated_token is not None:
                if (
                    identity["kind"] != "delegated_user"
                    or identity["user_object_id"].casefold() != self.settings.owner.casefold()
                    or identity["tenant_id"].casefold() != self.settings.tenant.casefold()
                    or identity["calling_application_id"].casefold() != self.settings.console_client_id.casefold()
                    or identity["audience"] not in {self.settings.gateway_client_id, f"api://{self.settings.gateway_client_id}"}
                    or "Gateway.Access" not in identity["delegated_scopes"]
                ):
                    raise ProtocolFailure("The OBO token did not match the allowed user, console application and APIM scope. No fallback was used.")
            elif identity["delegated_scopes"]:
                raise ProtocolFailure("The application-only comparison unexpectedly acquired a delegated token.")
            with httpx.Client(timeout=45, follow_redirects=False) as client:
                self.mcp(client, RunInput(action="mcp-list", gateway="apimv2", server="catalog"), headers)
            result = {
                "status": "passed", "identity": identity,
                "detail": "Read-only APIM catalog MCP discovery succeeded. Identity fields are acquired-token metadata; read the correlated gateway-stamped audit rows for confirmation.",
                "audit": {"status": "pending", "trace_id": tp.split("-")[1], "query": "01", "detail": "Allow for log ingestion, then read identity audit evidence."},
            }
        except (Unavailable, IdentityError) as error:
            result = {"status": "unavailable", "detail": str(error)}
        except ProtocolFailure as error:
            LOG.warning("identity_probe_protocol_failure mode=%s trace_id=%s", mode, tp.split("-")[1])
            result = {"status": "failed", "detail": str(error)}
        except (httpx.HTTPError, AzureError) as error:
            LOG.warning("identity_probe_upstream_failure mode=%s type=%s trace_id=%s", mode, type(error).__name__, tp.split("-")[1])
            result = {"status": "failed", "detail": f"{type(error).__name__}: the identity comparison could not reach or authenticate to APIM. No identity fallback was used."}
        result.update(action="identity", identity_mode=mode, trace_id=tp.split("-")[1], traceparent=tp)
        print(json.dumps({"event": "identity_probe", "identity_mode": mode, "trace_id": tp.split("-")[1], "outcome": result["status"]}), flush=True)
        encoded = json.dumps(result, default=str)
        for secret in secrets:
            if secret:
                encoded = encoded.replace(secret, "[redacted]")
        return json.loads(encoded)

    def gateway_url(self, gateway: str) -> str:
        url = self.settings.apim if gateway == "apimv2" else self.settings.aigateway
        if not url:
            raise Unavailable(f"{gateway} was not deployed/configured.")
        return url

    def headers(self, gateway: str, secrets: list[str]) -> dict[str, str]:
        if gateway == "apimv2":
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default").token
            secrets.append(token)
            return {"Authorization": f"Bearer {token}"}
        if self.settings.key_delivery == "env":
            key = self.settings.runtime_key
        elif self.settings.key_delivery == "keyvault" and self.settings.vault:
            with SecretClient(vault_url=self.settings.vault, credential=self.credential) as client:
                key = client.get_secret(self.settings.secret_name).value
        else:
            raise Unavailable("AI Gateway key delivery is not configured. Use keyvault or explicit env delivery.")
        if not key:
            raise Unavailable("AI Gateway runtime key is empty.")
        secrets.append(key)
        return {"api-key": key}

    def mcp_url(self, gateway: str, server: str) -> str:
        root = self.gateway_url(gateway)
        if gateway == "aigateway":
            return f"{root}/default/toolservers/{'catalog-mcp' if server == 'catalog' else 'records'}/mcp"
        return f"{root}/{'catalog-mcp' if server == 'catalog' else 'records-mcp'}/mcp"

    def model_url(self, gateway: str) -> str:
        root = self.gateway_url(gateway)
        return f"{root}/default/models/openai/v1/responses" if gateway == "aigateway" else f"{root}/{self.settings.llm_path}/openai/v1/responses"

    def mcp(
        self, client: httpx.Client, data: RunInput, headers: dict[str, str],
    ) -> tuple[str, dict[str, str], list[dict[str, Any]]]:
        url = self.mcp_url(data.gateway, data.server)
        headers = {**headers, "Accept": "application/json, text/event-stream"}
        response = client.post(url, headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "demo-console", "version": "1.0.0"}},
        })
        payload = rpc_payload(response, 1)
        if not payload["result"].get("protocolVersion"):
            raise ProtocolFailure(f"MCP initialize failed (HTTP {response.status_code}).")
        headers["MCP-Protocol-Version"] = payload["result"]["protocolVersion"]
        if response.headers.get("mcp-session-id"):
            headers["mcp-session-id"] = response.headers["mcp-session-id"]
        notification = client.post(url, headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        if not notification.is_success:
            raise ProtocolFailure(f"MCP initialized notification failed (HTTP {notification.status_code}).")
        response = client.post(url, headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        payload = rpc_payload(response, 2)
        tools = payload["result"].get("tools")
        if not isinstance(tools, list) or not all(isinstance(tool, dict) and isinstance(tool.get("name"), str) for tool in tools):
            raise ProtocolFailure(f"MCP tools/list failed (HTTP {response.status_code}).")
        return url, headers, tools

    def audit(self, data: RunInput) -> dict[str, Any]:
        if not self.settings.workspace:
            raise Unavailable("Log Analytics workspace is not configured.")
        files = sorted(audit_query_directory().glob(f"{data.query}-*.kql"))
        if len(files) != 1:
            raise Unavailable("Saved query is missing or ambiguous.")
        query = files[0].read_text(encoding="utf-8")
        attribution_warning = ""
        if data.query in {"02", "11"}:
            if self.settings.aigw_principal_id:
                try:
                    principal_id = str(uuid.UUID(self.settings.aigw_principal_id))
                except ValueError:
                    raise Unavailable("AIGW_PRINCIPAL_ID must be the gateway managed-identity principal GUID.") from None
                query = query.replace('let aigwPrincipalId = "";', f'let aigwPrincipalId = "{principal_id}";')
            elif self.settings.aigateway:
                attribution_warning = " AI Gateway token attribution is unavailable: AIGW_PRINCIPAL_ID is not configured."
        if data.query == "04" and data.trace_id:
            query = query.replace('traceId:string = ""', f'traceId:string = "{data.trace_id}"')
        if data.query == "01" and data.trace_id:
            query += f'\n| where trace_id == "{data.trace_id}"'
        with LogsQueryClient(self.credential) as client:
            response = client.query_workspace(self.settings.workspace, query + "\n| take 200", timespan=timedelta(hours=1))
        if response.status != LogsQueryStatus.SUCCESS:
            raise ProtocolFailure("Log Analytics returned partial results; inspect workspace permissions and query errors.")
        tables = [{"columns": table.columns, "rows": [list(row) for row in table.rows]} for table in response.tables]
        rows = sum(len(table["rows"]) for table in tables)
        return {
            "status": "passed" if rows else "not_run", "query": files[0].name, "tables": tables,
            "detail": (f"{rows} rows returned (last hour, at most 200 per table). Rows require interpretation; no automatic audit assertion." if rows else "No rows yet. Allow for ingestion delay; this is not proof of an audit pass.") + attribution_warning,
        }

    def execute(self, data: RunInput, client: httpx.Client, tp: str, secrets: list[str]) -> dict[str, Any]:
        canonical_tool = canonical_tool_name(data.gateway, data.server, data.tool)
        mutates = data.action in {"agent", "rest-create", "rest-update", "throttle"} or (
            data.action == "mcp-call" and canonical_tool in {"create_record", "update_record"}
        )
        if mutates and not data.confirmed:
            raise HTTPException(400, "Confirm agent/tool side effects or bounded throttle cost before running.")
        if data.action == "audit":
            return self.audit(data)
        headers = {"traceparent": tp, "Content-Type": "application/json"}
        if data.action == "agent":
            if not self.settings.project:
                raise Unavailable("Foundry project endpoint is not configured.")
            token = self.credential.get_token("https://ai.azure.com/.default").token
            secrets.append(token)
            headers["Authorization"] = f"Bearer {token}"
            url = f"{self.settings.project}/agents/agent-{data.agent}/endpoint/protocols/openai/responses?api-version=v1"
            response = client.post(url, headers=headers, json={"input": data.prompt, "stream": False}, timeout=90)
            payload = decode_payload(response)
            return {
                "status": "passed" if completed_response(response, payload) else "failed",
                "http_status": response.status_code, "response": payload,
                "detail": f"Hosted {data.agent}; configured gateway: {self.settings.agent_gateway} (provisioning snapshot, not live discovery). Protocol result only: verify tool use and trace propagation in S5. Gateway dropdown does not reconfigure hosted agents.",
            }
        if data.action == "unauthenticated":
            response = client.post(self.mcp_url(data.gateway, data.server), headers=headers, json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {},
            })
            return {"status": "passed" if response.status_code == 401 else "failed", "http_status": response.status_code, "detail": "Expected exactly HTTP 401 without credentials."}
        if data.action == "denied-tool" and data.gateway != "apimv2":
            raise Unavailable("Only APIM has the demonstrated explicit tool allow-list policy; do not equate a tier unknown-tool error with a gateway denial.")
        headers.update(self.headers(data.gateway, secrets))
        if data.action.startswith("mcp-") or data.action == "denied-tool":
            if data.action == "mcp-call" and canonical_tool not in TOOLS[data.server]:
                raise HTTPException(400, "Select a supported tool from this server's live tools/list.")
            url, session_headers, tools = self.mcp(client, data, headers)
            if data.action == "mcp-list":
                return {
                    "status": "passed",
                    "tools": [
                        {**tool, "console_supported": canonical_tool_name(data.gateway, data.server, tool["name"]) in TOOLS[data.server]}
                        for tool in tools
                    ],
                    "detail": "MCP initialize, notification and tools/list succeeded. Select a demo-enabled tool to exercise its live input schema; other advertised tools are disabled in this console.",
                }
            name = "delete_all_records" if data.action == "denied-tool" else data.tool
            if data.action == "mcp-call" and name not in {tool["name"] for tool in tools}:
                raise HTTPException(400, "Selected tool is not advertised by the live gateway.")
            response = client.post(url, headers=session_headers, json={
                "jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": name, "arguments": data.arguments},
            })
            payload = decode_payload(response, 3)
            allowed_denial = (
                response.status_code == 403 and isinstance(payload, dict)
                and isinstance(payload.get("error"), dict)
                and payload["error"].get("message") == "Tool is not permitted by the gateway allow-list."
            )
            result = payload.get("result") if isinstance(payload, dict) else None
            tool_ok = (
                successful(response, payload) and payload.get("jsonrpc") == "2.0" and payload.get("id") == 3
                and isinstance(result, dict) and isinstance(result.get("content"), list)
            )
            ok = allowed_denial if data.action == "denied-tool" else tool_ok
            return {"status": "passed" if ok else "failed", "http_status": response.status_code, "response": payload}
        if data.action.startswith("rest-"):
            if data.gateway != "apimv2":
                raise Unavailable("The REST route is APIM-only; use records MCP for the AI Gateway tier.")
            url = f"{self.gateway_url(data.gateway)}/records/"
            if data.action in {"rest-get", "rest-update"}:
                if not data.record_id:
                    raise HTTPException(400, "A record ID is required.")
                url += data.record_id
            method = {"rest-list": "GET", "rest-get": "GET", "rest-create": "POST", "rest-update": "PATCH"}[data.action]
            response = client.request(method, url, headers=headers, **({"json": data.arguments} if method != "GET" else {}))
            payload = decode_payload(response)
            return {"status": "passed" if response.is_success else "failed", "http_status": response.status_code, "response": payload}
        body = {
            "model": self.settings.model, "input": data.prompt, "stream": False,
            "max_output_tokens": 64 if data.action == "throttle" else 1024,
        }
        url = self.model_url(data.gateway)
        if data.action == "throttle":
            if not self.throttle_lock.acquire(blocking=False):
                raise HTTPException(409, "A throttle probe is already running.")
            try:
                deadline = time.monotonic() + 90
                def probe(_: int) -> int | None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None
                    try:
                        return client.post(url, headers=headers, json=body, timeout=min(15, remaining)).status_code
                    except httpx.HTTPError as exc:
                        LOG.warning("throttle_transport_failure type=%s", type(exc).__name__)
                        return 0
                with ThreadPoolExecutor(max_workers=min(8, data.attempts)) as pool:
                    codes = [code for code in pool.map(probe, range(data.attempts)) if code is not None]
            finally:
                self.throttle_lock.release()
            failures = [code for code in codes if code != 429 and not 200 <= code < 300]
            return {
                "status": "failed" if failures else ("passed" if 429 in codes else "not_run"),
                "attempts": len(codes), "requested_attempts": data.attempts,
                "http_status_counts": {str(code): codes.count(code) for code in sorted(set(codes))},
                "detail": "Observed HTTP 429; inspect gateway logs to distinguish gateway limits from backend throttling." if 429 in codes else "No HTTP 429 observed within the bounded budget. Not a policy pass. Zero denotes a transport failure.",
            }
        response = client.post(url, headers=headers, json=body)
        payload = decode_payload(response)
        return {
            "status": "passed" if completed_response(response, payload) else "failed",
            "http_status": response.status_code, "response": payload,
            "detail": "Direct call using the console managed identity (APIM) or runtime key (tier), not the hosted agent's identity or human OBO.",
        }

    def run(self, data: RunInput) -> dict[str, Any]:
        tp = f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"
        secrets: list[str] = [self.settings.runtime_key] if self.settings.runtime_key else []
        try:
            with httpx.Client(timeout=45, follow_redirects=False) as client:
                result = self.execute(data, client, tp, secrets)
        except Unavailable as exc:
            result = {"status": "unavailable", "detail": str(exc)}
        except ProtocolFailure as exc:
            LOG.warning("workflow_protocol_failure action=%s trace_id=%s", data.action, tp.split("-")[1])
            result = {"status": "failed", "detail": str(exc)}
        except (httpx.HTTPError, AzureError) as exc:
            LOG.warning("workflow_upstream_failure action=%s type=%s trace_id=%s", data.action, type(exc).__name__, tp.split("-")[1])
            result = {"status": "failed", "detail": f"{type(exc).__name__}: check managed identity permissions, endpoint/network reachability and Azure service health."}
        result.update(action=data.action, trace_id=tp.split("-")[1], traceparent=tp)
        encoded = json.dumps(result, default=str)
        for secret in secrets:
            encoded = encoded.replace(secret, "[redacted]")
        return json.loads(encoded)


def authorization_failure(request: Request, settings: Settings) -> str | None:
    if not settings.owner or not settings.tenant:
        return "missing_auth_configuration"
    platform_id = request.headers.get("x-ms-client-principal-id")
    platform_provider = request.headers.get("x-ms-client-principal-idp")
    if platform_provider and platform_provider.casefold() not in {"aad", "azureactivedirectory"}:
        return "unexpected_identity_provider"
    if platform_id and platform_id != settings.owner:
        return "owner_mismatch"
    encoded = request.headers.get("x-ms-client-principal")
    if not encoded:
        # ACA injects this ID only after Easy Auth validates the configured tenant.
        return None if platform_id else "missing_platform_identity"
    try:
        principal = json.loads(base64.b64decode(encoded, validate=True))
        claims = {claim["typ"]: claim["val"] for claim in principal.get("claims", [])}
        oid = claims.get("http://schemas.microsoft.com/identity/claims/objectidentifier") or claims.get("oid")
        tenant = claims.get("http://schemas.microsoft.com/identity/claims/tenantid") or claims.get("tid")
    except (ValueError, TypeError, KeyError, AttributeError, binascii.Error):
        return "invalid_platform_principal"
    if oid and oid != settings.owner:
        return "owner_mismatch"
    if tenant and tenant != settings.tenant:
        return "tenant_mismatch"
    if platform_id:
        return None
    if not oid or not tenant:
        return "incomplete_platform_principal"
    return None


def authorized(request: Request, settings: Settings) -> bool:
    return authorization_failure(request, settings) is None


def create_app(settings: Settings | None = None, runner: Runner | None = None, obo: UserObo | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="Secure Agents Demo Console", docs_url=None, redoc_url=None, openapi_url=None)
    runner = runner or Runner(settings)
    obo = obo or UserObo(settings, lambda token: runner.identity_probe(token))

    @app.middleware("http")
    async def guard(request: Request, call_next: Any) -> Any:
        oauth_callback = request.url.path == "/api/identity/obo/callback" and request.method == "POST"
        if request.url.path != "/healthz":
            auth_reason = None if oauth_callback else authorization_failure(request, settings)
            if auth_reason:
                LOG.warning("console_access_denied auth_reason=%s", auth_reason)
                return JSONResponse({
                    "detail": "Deployer-only access. Sign in through the Azure Container Apps Entra authentication endpoint.",
                    "auth_reason": auth_reason,
                }, status_code=403, headers={"Cache-Control": "no-store"})
            if request.method not in {"GET", "HEAD"}:
                if not oauth_callback and (request.headers.get("origin") != settings.origin or request.headers.get("x-demo-console") != "1"):
                    return JSONResponse({"detail": "Same-origin console requests only."}, status_code=403)
                length = request.headers.get("content-length", "0")
                if not length.isdigit():
                    return JSONResponse({"detail": "Invalid content length."}, status_code=400)
                if int(length) > 16384:
                    return JSONResponse({"detail": "Request exceeds 16 KiB."}, status_code=413)
                body = await request.body()
                if len(body) > 16384:
                    return JSONResponse({"detail": "Request exceeds 16 KiB."}, status_code=413)
        response = await call_next(request)
        response.headers.update({
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        })
        return response

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/reference/architecture.png")
    def architecture() -> FileResponse:
        image = Path("/reference/architecture.png")
        if not image.exists():
            image = ROOT / "docs" / "assets" / "foundry-hosted-agents-ai-gateway-landing-zone-architecture.png"
        if not image.is_file():
            raise HTTPException(503, "The reference architecture image is not bundled in this deployment.")
        return FileResponse(image, media_type="image/png")

    @app.get("/api/config")
    def config() -> dict[str, Any]:
        profile_dir = Path("/config/profiles") if Path("/config/profiles").exists() else ROOT / "config" / "profiles"
        if not re.fullmatch(r"[a-z0-9-]+", settings.profile):
            raise HTTPException(503, "Invalid domain profile configuration.")
        profile = json.loads((profile_dir / f"{settings.profile}.json").read_text(encoding="utf-8"))
        return {
            "profile": profile["displayName"], "walkthrough": profile["walkthrough"],
            "gateways": [name for name, url in (("apimv2", settings.apim), ("aigateway", settings.aigateway)) if url],
            "agent_gateway": settings.agent_gateway,
            "identity": "Default direct calls use console managed identity. Explicit S2 user OBO is separate from hosted-agent instance identity.",
            "queries": [
                {"id": path.name[:2], "label": path.stem.replace("-", " ")}
                for path in sorted(audit_query_directory().glob("*.kql"))
                if re.match(r"^(0[1-9]|1[01])-", path.name)
            ],
            "workbook_url": f"https://portal.azure.com/#resource{quote(settings.workbook_id, safe='/')}/workbook" if settings.workbook_id else None,
            "connections": {
                "foundry_project": bool(settings.project),
                "audit_workspace": bool(settings.workspace),
            },
            "obo": {
                "available": obo.unavailable_reason is None,
                "detail": obo.unavailable_reason or "Explicit user sign-in, console access token, genuine OBO exchange and read-only APIM call. Not hosted-agent delegation.",
            },
        }

    @app.post("/api/run")
    def run(data: RunInput) -> dict[str, Any]:
        return runner.run(data)

    @app.post("/api/identity/managed")
    def managed_identity() -> dict[str, Any]:
        return runner.identity_probe()

    @app.post("/api/identity/obo/start")
    def start_obo() -> JSONResponse:
        try:
            binding, url = obo.start()
        except IdentityError as error:
            raise HTTPException(error.status, str(error)) from None
        response = JSONResponse({"authorization_url": url})
        response.set_cookie(COOKIE_NAME, binding, max_age=FLOW_TTL, secure=True, httponly=True, samesite="none", path="/")
        return response

    @app.post("/api/identity/obo/callback")
    async def complete_obo(request: Request) -> RedirectResponse:
        if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/x-www-form-urlencoded":
            raise HTTPException(415, "The OAuth callback requires a form-post response.")
        try:
            fields = parse_qsl((await request.body()).decode("utf-8"), keep_blank_values=True, max_num_fields=12)
        except ValueError:
            raise HTTPException(400, "Invalid OAuth form response.") from None
        if len({key for key, _ in fields}) != len(fields):
            raise HTTPException(400, "Repeated OAuth response parameters are not accepted.")
        binding = request.cookies.get(COOKIE_NAME, "")
        try:
            await run_in_threadpool(obo.complete, binding, dict(fields))
        except IdentityError as error:
            raise HTTPException(error.status, str(error)) from None
        response = RedirectResponse("/identity/obo/complete", status_code=303)
        response.set_cookie(COOKIE_NAME, binding, max_age=RESULT_TTL, secure=True, httponly=True, samesite="none", path="/")
        return response

    @app.get("/identity/obo/complete")
    def obo_complete_page() -> FileResponse:
        return FileResponse(STATIC / "obo-complete.html")

    @app.get("/api/identity/obo/result")
    def obo_result(request: Request) -> JSONResponse:
        try:
            result = obo.take_result(request.cookies.get(COOKIE_NAME, ""))
        except IdentityError as error:
            raise HTTPException(error.status, str(error)) from None
        response = JSONResponse(result)
        if result["status"] != "not_run":
            response.delete_cookie(COOKIE_NAME, secure=True, httponly=True, samesite="none", path="/")
        return response

    @app.post("/api/identity/obo/cancel")
    def cancel_obo(request: Request) -> JSONResponse:
        obo.cancel(request.cookies.get(COOKIE_NAME, ""))
        response = JSONResponse({"status": "not_run", "detail": "Pending user sign-in cancelled; no identity fallback was used."})
        response.delete_cookie(COOKIE_NAME, secure=True, httponly=True, samesite="none", path="/")
        return response

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
