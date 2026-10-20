from __future__ import annotations

import sys

import httpx
import pytest

from conftest import ROOT, load_module


@pytest.fixture
def walkthrough():
    return load_module("demo_walkthrough_test", ROOT / "scripts" / "demo_walkthrough.py")


def test_dry_run_is_a_plan_not_live_acceptance(walkthrough, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["demo_walkthrough.py", "--dry-run", "--agent", "both"])
    monkeypatch.setattr(walkthrough, "invoke_agent", lambda *_: pytest.fail("A plan must not make network calls."))
    assert walkthrough.main() == 0
    output = capsys.readouterr().out
    assert output.count("PLAN") == 10
    assert "PASS" not in output
    assert "Expected gateway" in output


def test_unimplemented_steps_are_not_passes(walkthrough, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["demo_walkthrough.py"])
    monkeypatch.setattr(walkthrough, "invoke_agent", lambda *_: (True, "Fixture completed response only."))
    assert walkthrough.main() == 2
    output = capsys.readouterr().out
    assert output.count("NOT_RUN") == 4
    assert output.count("PASS") == 1
    assert "not live routing discovery" in output


def test_a_failed_response_still_fails_the_rehearsal(walkthrough, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["demo_walkthrough.py", "--step", "S1"])
    monkeypatch.setattr(walkthrough, "invoke_agent", lambda *_: (False, "Fixture response failed."))
    assert walkthrough.main() == 1


@pytest.mark.parametrize("payload,expected", [
    ({}, False),
    ({"status": "failed", "output": []}, False),
    ({"status": "incomplete", "output": []}, False),
    ({"status": "completed"}, False),
    ({"status": "completed", "output": [], "error": {"code": "test"}}, False),
    ({"status": "completed", "output": []}, True),
])
def test_invoke_requires_a_completed_responses_payload(walkthrough, monkeypatch, payload, expected):
    monkeypatch.setattr(walkthrough, "ai_token", lambda: "fixture-token")
    monkeypatch.setattr(walkthrough.httpx, "post", lambda *_, **__: httpx.Response(200, json=payload))
    ok, detail = walkthrough.invoke_agent("maf", {"foundryProjectEndpoint": "https://project.example"}, "Fixture prompt")
    assert ok is expected
    assert "verify propagation separately" in detail
    assert "fixture-token" not in detail


def test_non_json_response_is_not_a_pass(walkthrough, monkeypatch):
    monkeypatch.setattr(walkthrough, "ai_token", lambda: "fixture-token")
    monkeypatch.setattr(walkthrough.httpx, "post", lambda *_, **__: httpx.Response(200, text="not JSON"))
    ok, detail = walkthrough.invoke_agent("maf", {"foundryProjectEndpoint": "https://project.example"}, "Fixture prompt")
    assert not ok and "not JSON" in detail
