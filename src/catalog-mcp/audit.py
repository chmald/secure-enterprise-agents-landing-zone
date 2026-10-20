
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Mapping

LOGGER = logging.getLogger("tool_audit")
TRACEPARENT_ZERO_TRACE = "00000000000000000000000000000000"
TRACEPARENT_ZERO_SPAN = "0000000000000000"
SENSITIVE_KEYS = {"authorization", "api-key", "ocp-apim-subscription-key", "x-api-key", "token", "access_token"}


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")


def configure_azure_monitor_if_available() -> None:
    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        return
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=connection_string)
    except Exception as exc:
        LOGGER.warning(json.dumps({"event": "telemetry_setup_failed", "reason": str(exc)}))


def parse_traceparent(traceparent: str | None) -> tuple[str | None, str | None]:
    if not traceparent:
        return None, None
    parts = traceparent.split("-")
    if len(parts) < 4:
        return None, None
    trace_id, span_id = parts[1], parts[2]
    if len(trace_id) != 32 or len(span_id) != 16 or trace_id == TRACEPARENT_ZERO_TRACE or span_id == TRACEPARENT_ZERO_SPAN:
        return None, None
    return trace_id, span_id


def _header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def gateway_principals(headers: Mapping[str, str]) -> tuple[dict[str, str | None] | None, dict[str, str | None]]:
    human_oid = _header(headers, "x-gw-user-oid")
    appid = _header(headers, "x-gw-agent-appid")
    oid = _header(headers, "x-gw-agent-oid")
    actor_facets = _header(headers, "x-gw-actor-facets")
    human = {"oid": human_oid, "name": _header(headers, "x-gw-user-name"), "username": _header(headers, "x-gw-user-username")} if human_oid else None
    agent = {"appid": appid, "oid": oid, "actor_facets": actor_facets}
    return human, agent


def gateway_context(headers: Mapping[str, str]) -> tuple[str | None, str | None]:
    caller = _header(headers, "x-gw-caller")
    if caller:
        return "aigateway", caller
    has_gateway_headers = any(key.lower().startswith("x-gw-") for key in headers)
    return ("apimv2" if has_gateway_headers else None), None


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: ("***redacted***" if key.lower() in SENSITIVE_KEYS else value) for key, value in values.items()}


def build_audit_record(*, service: str, tool: str, operation: str, decision: str, reason: str, headers: Mapping[str, str], domain_profile: str, latency_ms: float, status_code: int) -> dict[str, Any]:
    traceparent = _header(headers, "traceparent")
    trace_id, span_id = parse_traceparent(traceparent)
    human, agent = gateway_principals(headers)
    gateway, caller = gateway_context(headers)
    identity_type = "delegated_user" if human else "application" if agent["oid"] else "runtime_key" if caller else "unattributed"
    return {"event":"tool_audit","timestamp":datetime.now(timezone.utc).isoformat(),"trace_id":trace_id,"span_id":span_id,"traceparent":traceparent,"service":service,"tool":tool,"operation":operation,"decision":decision,"reason":reason,"human_principal":human,"agent_principal":agent,"identity_type":identity_type,"delegated_scopes":_header(headers,"x-gw-delegated-scopes") if human else None,"gateway_request_id":_header(headers,"x-gw-request-id"),"gateway":gateway,"caller":caller,"domain_profile":domain_profile,"latency_ms":round(latency_ms,2),"status_code":status_code}


def emit_audit_record(record: Mapping[str, Any]) -> None:
    print(json.dumps(record, separators=(",", ":")), flush=True)


class AuditTimer:
    def __enter__(self) -> "AuditTimer":
        self.started = time.perf_counter()
        return self
    def __exit__(self, *_: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self.started) * 1000
