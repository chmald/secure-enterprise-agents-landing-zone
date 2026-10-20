from __future__ import annotations

import base64
import json
import logging
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import ROOT, load_module

TENANT = "11111111-1111-4111-8111-111111111111"
CONSOLE = "22222222-2222-4222-8222-222222222222"
FRONTEND = "33333333-3333-4333-8333-333333333333"
GATEWAY = "44444444-4444-4444-8444-444444444444"


@pytest.fixture
def console():
    return load_module("identity_console_test", ROOT / "src" / "demo-console" / "app.py")


@pytest.fixture
def settings(console):
    return console.Settings(
        tenant=TENANT, owner="allowed-owner", origin="https://console.example", apim="https://apim.example",
        enable_obo=True, console_client_id=CONSOLE, console_client_secret="private-console-secret",
        obo_client_id=FRONTEND, obo_client_secret="private-frontend-secret", gateway_client_id=GATEWAY,
    )


def token(**claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "eyJhbGciOiJub25lIn0." + payload + ".fixture-signature"


class FakeClient:
    def __init__(self, client_id, calls, owner="allowed-owner", token_error=None):
        self.client_id, self.calls, self.owner, self.token_error = client_id, calls, owner, token_error

    def initiate_auth_code_flow(self, **kwargs):
        self.calls.append(("start", self.client_id, kwargs))
        return {"state": "fixed-state", "nonce": "fixture-nonce", "auth_uri": "https://login.microsoftonline.com/" + TENANT + "/oauth2/v2.0/authorize"}

    def acquire_token_by_auth_code_flow(self, flow, response, scopes):
        self.calls.append(("authorization_code", self.client_id, scopes))
        assert flow["state"] == response["state"]
        return {"access_token": "user-access-token-for-console", "id_token": "not-an-obo-assertion", "id_token_claims": {"oid": self.owner, "tid": TENANT}}

    def acquire_token_on_behalf_of(self, **kwargs):
        self.calls.append(("obo", self.client_id, kwargs))
        return self.token_error or {"access_token": "user-access-token-for-gateway"}


def make_service(console, settings, owner="allowed-owner", token_error=None, clock=lambda: 0):
    calls = []
    probe = lambda access_token: calls.append(("probe", access_token)) or {"status": "passed", "trace_id": "a" * 32}
    service = console.UserObo(
        settings, probe,
        client_factory=lambda client_id, secret: FakeClient(client_id, calls, owner=owner, token_error=token_error),
        clock=clock,
    )
    return service, calls


def test_real_grant_chain_uses_console_access_token_not_id_token(console, settings):
    service, calls = make_service(console, settings)
    binding, url = service.start()
    assert "login.microsoftonline.com" in url
    service.complete(binding, {"state": "fixed-state", "code": "one-use-code"})
    assert service.take_result(binding)["status"] == "passed"
    assert calls[1] == ("authorization_code", FRONTEND, [f"api://{CONSOLE}/Console.Access"])
    assert calls[2] == ("obo", CONSOLE, {"user_assertion": "user-access-token-for-console", "scopes": [f"api://{GATEWAY}/Gateway.Access"]})
    assert calls[3] == ("probe", "user-access-token-for-gateway")
    with pytest.raises(console.IdentityError):
        service.take_result(binding)


def test_flow_state_browser_binding_and_replay_are_enforced(console, settings):
    service, calls = make_service(console, settings)
    binding, _ = service.start()
    for cookie, state in (("other-browser", "fixed-state"), (binding, "wrong-state")):
        with pytest.raises(console.IdentityError):
            service.complete(cookie, {"state": state, "code": "one-use-code"})
    assert len(calls) == 1
    service.complete(binding, {"state": "fixed-state", "code": "one-use-code"})
    with pytest.raises(console.IdentityError) as error:
        service.complete(binding, {"state": "fixed-state", "code": "one-use-code"})
    assert error.value.status == 409
    assert len([call for call in calls if call[0] == "obo"]) == 1


def test_different_user_cannot_exchange_or_call_apim(console, settings):
    service, calls = make_service(console, settings, owner="other-owner")
    binding, _ = service.start()
    service.complete(binding, {"state": "fixed-state", "code": "one-use-code"})
    assert service.take_result(binding)["status"] == "failed"
    assert not any(call[0] in {"obo", "probe"} for call in calls)


def test_consent_failure_is_explicit_and_does_not_fall_back_or_leak(console, settings, caplog):
    service, calls = make_service(console, settings, token_error={
        "error": "invalid_grant", "error_codes": [65001], "error_description": "private-token-and-secret",
    })
    binding, _ = service.start()
    service.complete(binding, {"state": "fixed-state", "code": "one-use-code"})
    result = service.take_result(binding)
    assert result["status"] == "failed" and "65001" in result["detail"]
    assert not any(call[0] == "probe" for call in calls)
    assert "private-token-and-secret" not in json.dumps(result) + caplog.text


def test_expired_disabled_and_full_flow_store_fail_closed(console, settings):
    now = [0]
    service, _ = make_service(console, settings, clock=lambda: now[0])
    binding, _ = service.start()
    now[0] = 601
    with pytest.raises(console.IdentityError):
        service.complete(binding, {"state": "fixed-state", "code": "one-use-code"})
    disabled, _ = make_service(console, replace(settings, enable_obo=False))
    with pytest.raises(console.IdentityError) as error:
        disabled.start()
    assert error.value.status == 503
    for _ in range(16):
        service.start()
    with pytest.raises(console.IdentityError) as error:
        service.start()
    assert error.value.status == 429


def test_secure_cookie_and_authorized_callback_round_trip(console, settings):
    service, _ = make_service(console, settings)
    client = TestClient(console.create_app(settings, obo=service), base_url=settings.origin)
    headers = {"x-ms-client-principal-id": settings.owner, "Origin": settings.origin, "X-Demo-Console": "1"}
    assert client.post("/api/identity/obo/start").status_code == 403
    start = client.post("/api/identity/obo/start", headers=headers)
    assert start.status_code == 200
    cookie = start.headers["set-cookie"]
    assert "__Host-demo-obo=" in cookie and "HttpOnly" in cookie and "Secure" in cookie and "SameSite=none" in cookie
    assert "private-" not in start.text and "code_verifier" not in start.text
    response = client.post("/api/identity/obo/callback", data={"state": "fixed-state", "code": "one-use-code"}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/identity/obo/complete"
    result = client.get("/api/identity/obo/result", headers=headers)
    assert result.json()["status"] == "passed"
    assert client.get("/api/identity/obo/result", headers=headers).status_code == 401


def test_callback_duplicate_state_and_missing_browser_cookie_are_rejected(console, settings):
    service, calls = make_service(console, settings)
    client = TestClient(console.create_app(settings, obo=service), base_url=settings.origin)
    headers = {"x-ms-client-principal-id": settings.owner}
    form = {"Content-Type": "application/x-www-form-urlencoded"}
    assert client.post("/api/identity/obo/callback", headers=form, content="state=x&state=y&code=z").status_code == 400
    assert client.post("/api/identity/obo/callback", headers=form, content="state=x&code=z").status_code == 401
    assert client.post("/api/identity/obo/callback", json={"state": "x", "code": "z"}).status_code == 415
    assert not calls


def test_token_metadata_and_probe_never_return_raw_tokens(console, settings, monkeypatch):
    acquired = token(oid=settings.owner, tid=TENANT, azp=CONSOLE, aud=GATEWAY, scp="Gateway.Access", name="Synthetic User", preferred_username="operator@example.test")
    original = httpx.Client
    def handler(request):
        message = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer " + acquired
        if message["method"] == "notifications/initialized":
            return httpx.Response(202)
        result = {"protocolVersion": "2025-06-18"} if message["method"] == "initialize" else {"tools": []}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": message["id"], "result": result})
    monkeypatch.setattr(console.httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result = console.Runner(settings, SimpleNamespace()).identity_probe(acquired)
    assert result["status"] == "passed" and result["identity_mode"] == "user_obo"
    assert result["identity"]["user_username"] == "operator@example.test"
    assert result["identity"]["calling_application_id"] == CONSOLE
    assert acquired not in json.dumps(result) and "private-" not in json.dumps(result)
    wrong = token(oid="other", tid=TENANT, azp=CONSOLE, aud=GATEWAY, scp="Gateway.Access")
    assert console.Runner(settings, SimpleNamespace()).identity_probe(wrong)["status"] == "failed"


def test_callback_authorization_code_is_redacted_from_access_log(console):
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 1, '%s - "%s %s HTTP/%s" %s', (
        "client", "GET", "/api/identity/obo/callback?code=private-code&state=private-state", "1.1", 303,
    ), None)
    console.OAuthCallbackAccessFilter().filter(record)
    assert "/api/identity/obo/callback" in record.getMessage()
    assert "private-code" not in record.getMessage() and "private-state" not in record.getMessage()


def test_cancelled_sign_in_cannot_exchange_or_probe(console, settings):
    service, calls = make_service(console, settings)
    binding, _ = service.start()
    service.cancel(binding)
    with pytest.raises(console.IdentityError):
        service.complete(binding, {"state": "fixed-state", "code": "one-use-code"})
    assert not any(call[0] in {"obo", "probe"} for call in calls)


def test_identity_audit_query_filters_to_the_selected_trace(console, settings, monkeypatch):
    seen = []
    class Logs:
        def __init__(self, credential): pass
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def query_workspace(self, workspace, query, timespan):
            seen.append(query)
            return SimpleNamespace(status=console.LogsQueryStatus.SUCCESS, tables=[])
    monkeypatch.setattr(console, "LogsQueryClient", Logs)
    runner = console.Runner(replace(settings, workspace="workspace"), SimpleNamespace())
    runner.audit(console.RunInput(action="audit", query="01", trace_id="a" * 32))
    assert '| where trace_id == "' + "a" * 32 + '"' in seen[0]
    assert seen[0].endswith("| take 200")


def test_id_token_alone_is_never_an_obo_assertion(console, settings):
    calls = []
    class IdTokenClient(FakeClient):
        def acquire_token_by_auth_code_flow(self, flow, response, scopes):
            return {"id_token": "not-a-user-access-token", "id_token_claims": {"oid": settings.owner, "tid": TENANT}}
    service = console.UserObo(
        settings, lambda _: pytest.fail("An ID token must not reach APIM."),
        client_factory=lambda client_id, secret: IdTokenClient(client_id, calls),
    )
    binding, _ = service.start()
    service.complete(binding, {"state": "fixed-state", "code": "code"})
    result = service.take_result(binding)
    assert result["status"] == "failed" and "user sign-in failed" in result["detail"]
    assert not any(call[0] == "obo" for call in calls)


def test_cancellation_during_exchange_prevents_the_apim_probe(console, settings):
    calls = []
    service = None
    binding = None
    class CancelClient(FakeClient):
        def acquire_token_on_behalf_of(self, **kwargs):
            service.cancel(binding)
            return {"access_token": "cancelled-gateway-token"}
    service = console.UserObo(
        settings, lambda _: pytest.fail("A cancelled exchange must not start an APIM request."),
        client_factory=lambda client_id, secret: CancelClient(client_id, calls),
    )
    binding, _ = service.start()
    service.complete(binding, {"state": "fixed-state", "code": "code"})
    with pytest.raises(console.IdentityError):
        service.take_result(binding)
