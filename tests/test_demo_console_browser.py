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
        def run(self, data):
            calls.append(data)
            if data.action == "agent" and not data.confirmed:
                raise console.HTTPException(400, "Confirm agent side effects.")
            result = {"status": "passed", "trace_id": "a" * 32, "detail": "Browser fixture, not Azure live evidence."}
            if data.action == "mcp-list":
                result["tools"] = [{
                    "name": "create_record",
                    "inputSchema": {"type": "object", "required": ["title"], "properties": {"title": {"type": "string"}}},
                }]
            if data.action == "model":
                result["response"] = "<script>window.untrustedContentExecuted = true</script>"
            return result

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
    app = console.create_app(console.Settings(
        tenant="browser-tenant", owner="browser-owner", origin=origin, apim="https://apim.example",
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
            page.locator("#prompt-preset").select_option(label="S3 / Tools/MCP")
            assert "PRT-100" in page.locator("#prompt").input_value()
            page.locator("[data-action=agent]").click()
            page.wait_for_function("() => document.getElementById('summary').textContent.includes('Confirm')")
            page.locator("#agent-confirm").check()
            page.locator("[data-action=agent]").click()
            page.wait_for_function("() => document.getElementById('status').textContent === 'passed'")
            assert not page.locator("#agent-confirm").is_checked()
            assert calls[-1].confirmed
            page.locator("[data-step=S2]").click()
            page.locator("[data-action=model]").click()
            page.wait_for_function("() => document.getElementById('result').textContent.includes('<script>')")
            assert page.evaluate("() => window.untrustedContentExecuted") is None
            assert page.locator("#trace-id").input_value() == "a" * 32
            page.locator("[data-step=S3]").click()
            page.locator("#server").select_option("records")
            page.locator("[data-action=mcp-list]").click()
            page.wait_for_selector("#tool option[value=create_record]", state="attached")
            page.locator("#tool").select_option("create_record")
            assert json.loads(page.locator("#arguments").input_value()) == {"title": ""}
            page.locator("#arguments").fill('{"title":"Synthetic browser record"}')
            page.locator("#write-confirm").check()
            page.locator("[data-action=mcp-call]").click()
            page.wait_for_function("() => document.getElementById('history').children.length === 4")
            assert calls[-1].arguments == {"title": "Synthetic browser record"}
            assert calls[-1].confirmed
            page.locator("#server").select_option("catalog")
            assert page.locator("#tool").input_value() == ""
            assert not page.locator("#write-confirm").is_checked()
            page.locator("[data-step=S4]").click()
            page.locator("#attempts").fill("8")
            page.locator("#throttle-confirm").check()
            page.locator("[data-action=throttle]").click()
            page.wait_for_function("() => document.getElementById('history').children.length === 5")
            assert calls[-1].attempts == 8 and calls[-1].confirmed
            page.locator("[data-step=S5]").click()
            page.locator("#query").select_option("04")
            page.locator("[data-action=audit]").click()
            page.wait_for_function("() => document.getElementById('history').children.length === 6")
            assert calls[-1].trace_id == "a" * 32
            assert not errors
            directory = Path(os.environ.get("CONSOLE_SCREENSHOT_DIR", tmp_path))
            directory.mkdir(parents=True, exist_ok=True)
            page.locator("[data-step=S1]").click()
            page.screenshot(path=str(directory / "console-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(directory / "console-mobile.png"), full_page=True)
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
