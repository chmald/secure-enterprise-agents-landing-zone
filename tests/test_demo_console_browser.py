from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from conftest import ROOT, load_module


def test_console_workflows_in_browser(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api", reason="Optional browser test: install playwright and Microsoft Edge.")
    console = load_module("browser_console", ROOT / "src/demo-console/app.py")
    calls = []

    class FixtureRunner:
        def identity_probe(self, delegated_token=None):
            return {
                "status": "passed", "identity_mode": "console_managed_identity", "trace_id": "a" * 32,
                "detail": "Browser identity fixture, not Azure live evidence.",
                "identity": {
                    "principal_object_id": "synthetic-console", "calling_application_id": "synthetic-client",
                    "tenant_id": "browser-tenant", "audience": "https://cognitiveservices.azure.com",
                    "user_object_id": None, "user_name": None, "user_username": None,
                    "delegated_scopes": [], "application_roles": [],
                },
            }

        def run(self, data):
            calls.append(data)
            if data.action in {"agent", "rest-create", "rest-update", "throttle"} and not data.confirmed:
                raise console.HTTPException(400, "Confirm agent side effects.")
            result = {"status": "passed", "trace_id": "a" * 32, "detail": "Browser fixture, not Azure live evidence."}
            if data.action == "mcp-list":
                name = "create_record" if data.server == "records" else "check_availability"
                field = "title" if data.server == "records" else "item_id"
                result["tools"] = [{
                    "name": f"{data.server}_{name}" if data.gateway == "aigateway" else name,
                    "inputSchema": {"type": "object", "required": [field], "properties": {field: {"type": "string"}}},
                    "console_supported": True,
                }, {"name": "extra_health_probe", "inputSchema": {"type": "object"}, "console_supported": False}]
            if data.action == "model":
                result["response"] = "<script>window.untrustedContentExecuted = true</script>"
            if data.action == "audit" and data.query == "01":
                result["tables"] = [{"columns": ["trace_id", "identity_type", "human_oid", "human_name", "human_username"], "rows": [[data.trace_id, "application", "", "", ""]]}]
            return result

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
    app = console.create_app(console.Settings(
        tenant="browser-tenant", owner="browser-owner", origin=origin, apim="https://apim.example", aigateway="https://tier.example",
        workbook_id="/subscriptions/test-sub/resourceGroups/demo/providers/Microsoft.Insights/workbooks/test-book",
    ), FixtureRunner())
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(.05)
    assert server.started
    try:
        with playwright.sync_playwright() as engine:
            try:
                browser = engine.chromium.launch(channel="msedge", headless=True)
            except playwright.Error as exc:
                pytest.skip(f"Microsoft Edge browser unavailable: {exc}")
            context = browser.new_context(extra_http_headers={"x-ms-client-principal-id": "browser-owner"}, viewport={"width": 1440, "height": 1100})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin)
            page.wait_for_selector("#profile:text('Manufacturing Field Operations')")
            page.wait_for_function("() => !document.querySelector('[data-action=agent]').disabled")
            assert not calls
            assert page.locator("#gateway option[value=apimv2]").inner_text() == "APIM v2 (Entra)"
            assert "not live discovery" in page.locator("#agent-route").inner_text()
            assert "who called which tool" in page.locator("#query option[value='01']").inner_text()
            assert page.locator("#workbook-link").get_attribute("href").endswith("/workbooks/test-book/workbook")
            page.locator("#session-guide > summary").click()
            assert page.locator("#session-guide > ol > li").count() == 8
            page.wait_for_function("() => document.getElementById('architecture').naturalWidth > 0")
            page.locator("[data-agenda-step=S3]").click()
            assert page.locator("#S3").is_visible()
            page.locator("#session-guide [data-agenda-step=S1]").click()
            page.locator("#session-guide > summary").click()
            page.locator("#prompt-preset").select_option(label="S3 / Tools/MCP")
            assert "PRT-100" in page.locator("#prompt").input_value()
            page.locator("[data-action=agent]").click()
            page.wait_for_function("() => document.getElementById('summary').textContent.includes('Confirm')")
            page.locator("#agent-confirm").check()
            page.locator("#agent").select_option("langgraph")
            assert not page.locator("#agent-confirm").is_checked()
            page.locator("#agent-confirm").check()
            page.locator("[data-action=agent]").click()
            page.wait_for_function("() => document.getElementById('status').textContent === 'passed'")
            assert not page.locator("#agent-confirm").is_checked()
            assert calls[-1].confirmed
            assert calls[-1].agent == "langgraph"
            def perform(action):
                expected = page.locator("#history > li").count() + 1
                page.locator(f"[data-action={action}]").click()
                page.wait_for_function("(count) => document.getElementById('history').children.length === count", arg=expected)
                assert calls[-1].action == ("audit" if action == "identity-audit" else action)

            page.locator("[data-step=S2]").click()
            perform("unauthenticated")
            perform("model")
            page.wait_for_function("() => document.getElementById('result').textContent.includes('<script>')")
            assert page.evaluate("() => window.untrustedContentExecuted") is None
            assert page.locator("#trace-id").input_value() == "a" * 32
            expected = page.locator("#history > li").count() + 1
            page.locator("#managed-identity-call").click()
            page.wait_for_function("(count) => document.getElementById('history').children.length === count", arg=expected)
            assert "synthetic-console" in page.locator("#identity-fields").inner_text()
            assert "None (application-only)" in page.locator("#identity-fields").inner_text()
            assert page.locator("#obo-call").is_disabled()
            perform("identity-audit")
            assert calls[-1].query == "01" and calls[-1].trace_id == "a" * 32
            assert "identity_type" in page.locator("#identity-audit-result").inner_text()
            page.locator("[data-step=S3]").click()
            page.locator("#server").select_option("records")
            perform("mcp-list")
            assert page.locator("#tool option[value=extra_health_probe]").evaluate("(option) => option.disabled")
            page.locator("#tool").focus()
            page.keyboard.press("End")
            assert page.locator("#tool").input_value() == "create_record"
            page.wait_for_selector("#tool option[value=create_record]", state="attached")
            page.locator("#tool").select_option("create_record")
            assert json.loads(page.locator("#arguments").input_value()) == {"title": ""}
            page.locator("#arguments").fill('{"title":"Synthetic browser record"}')
            page.locator("#write-confirm").check()
            perform("mcp-call")
            assert calls[-1].arguments == {"title": "Synthetic browser record"}
            assert calls[-1].confirmed
            perform("denied-tool")
            perform("rest-list")
            page.locator("#record-id").fill("REC-001")
            perform("rest-get")
            assert calls[-1].record_id == "REC-001"
            page.locator("#arguments").fill('{"title":"Synthetic REST record"}')
            page.locator("#write-confirm").check()
            perform("rest-create")
            assert calls[-1].confirmed
            page.locator("#arguments").fill('{"status":"completed"}')
            page.locator("#write-confirm").check()
            page.locator("#record-id").fill("REC-002")
            assert not page.locator("#write-confirm").is_checked()
            page.locator("#write-confirm").check()
            perform("rest-update")
            assert calls[-1].record_id == "REC-002" and calls[-1].arguments == {"status": "completed"}
            page.locator("#server").select_option("catalog")
            assert page.locator("#tool").input_value() == ""
            assert not page.locator("#write-confirm").is_checked()
            page.locator("#gateway").select_option("aigateway")
            assert "OpenAPI-generated" in page.locator("#tool-path").inner_text()
            assert "OpenAPI-generated" in page.locator("#server option[value=records]").inner_text()
            for button in page.locator("[data-apim-only]").all():
                assert button.is_disabled()
            perform("mcp-list")
            for button in page.locator("[data-apim-only]").all():
                assert button.is_disabled()
            page.locator("#tool").select_option("catalog_check_availability")
            page.locator("#arguments").fill('{"item_id":"ITEM-001"}')
            perform("mcp-call")
            assert calls[-1].gateway == "aigateway" and calls[-1].tool == "catalog_check_availability"
            page.locator("#gateway").select_option("apimv2")
            assert "not an APIM-generated MCP server" in page.locator("#tool-path").inner_text()
            assert not page.locator("[data-action=denied-tool]").is_disabled()
            page.locator("[data-step=S4]").click()
            page.locator("#attempts").fill("8")
            page.locator("#throttle-confirm").check()
            perform("throttle")
            assert calls[-1].attempts == 8 and calls[-1].confirmed
            page.locator("[data-step=S5]").click()
            page.locator("#query").select_option("04")
            perform("audit")
            assert calls[-1].trace_id == "a" * 32
            assert not errors
            directory = Path(os.environ.get("CONSOLE_SCREENSHOT_DIR", tmp_path))
            directory.mkdir(parents=True, exist_ok=True)
            page.locator("[data-step=S1]").click()
            page.screenshot(path=str(directory / "console-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(directory / "console-mobile.png"), full_page=True)
            page.locator("#session-guide > summary").click()
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(directory / "console-session-guide.png"), full_page=True)
            def obo_config(route):
                response = route.fetch()
                config = response.json()
                config["obo"] = {"available": True, "detail": "Browser fixture only; not real Entra configuration."}
                route.fulfill(response=response, json=config)
            page.route("**/api/config", obo_config)
            page.route("**/api/identity/obo/start", lambda route: route.fulfill(json={"authorization_url": origin + "/identity/obo/complete"}))
            delegated = {
                "status": "passed", "identity_mode": "user_obo", "trace_id": "b" * 32,
                "detail": "Browser user-OBO fixture only; not an actual Entra exchange.",
                "identity": {
                    "principal_object_id": "synthetic-user", "calling_application_id": "synthetic-console-app",
                    "tenant_id": "browser-tenant", "audience": "synthetic-gateway",
                    "user_object_id": "synthetic-user", "user_name": "Synthetic Operator",
                    "user_username": "operator@example.test", "delegated_scopes": ["Gateway.Access"], "application_roles": [],
                },
            }
            page.route("**/api/identity/obo/result", lambda route: route.fulfill(json=delegated))
            page.reload()
            page.wait_for_function("() => !document.getElementById('obo-call').disabled")
            page.locator("[data-step=S2]").click()
            page.locator("#obo-call").click()
            page.wait_for_function("() => document.getElementById('identity-fields').textContent.includes('operator@example.test')")
            assert "user_obo" in page.locator("#identity-fields").inner_text()
            assert page.locator("#trace-id").input_value() == "b" * 32
            page.screenshot(path=str(directory / "console-user-identity-fixture.png"), full_page=True)
            page.unroute("**/api/config")
            page.route("**/api/config", lambda route: route.fulfill(status=503, json={"detail": "Fixture configuration unavailable."}))
            page.reload()
            page.wait_for_function("() => document.getElementById('status').textContent === 'failed'")
            for button in page.locator("[data-action]").all():
                assert button.is_disabled()
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
