
import filecmp, json
from conftest import ROOT, load_module

def test_audit_modules_identical_and_schema_has_no_token_leak():
    catalog=ROOT/"src"/"catalog-mcp"/"audit.py"; records=ROOT/"src"/"records-api"/"audit.py"; assert filecmp.cmp(catalog,records,shallow=False)
    module=load_module("audit_test", catalog); record=module.build_audit_record(service="svc",tool="tool",operation="op",decision="allowed",reason="ok",headers={"traceparent":"00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01","authorization":"Bearer secret","x-gw-agent-appid":"app","x-gw-agent-oid":"oid","x-gw-user-oid":"user","x-gw-request-id":"req"},domain_profile="manufacturing-field-ops",latency_ms=12.345,status_code=200)
    for key in ["timestamp","trace_id","span_id","traceparent","service","tool","operation","decision","reason","human_principal","agent_principal","gateway_request_id","gateway","caller","domain_profile","latency_ms","status_code"]: assert key in record
    assert "secret" not in json.dumps(record).lower(); assert record["human_principal"]["oid"]=="user"; assert record["agent_principal"]["appid"]=="app"; assert record["gateway"]=="apimv2"; assert record["caller"] is None
    aigw=module.build_audit_record(service="svc",tool="tool",operation="op",decision="allowed",reason="ok",headers={"traceparent":"00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01","x-gw-caller":"aigw-runtime-key:agents"},domain_profile="manufacturing-field-ops",latency_ms=1,status_code=200)
    assert aigw["gateway"]=="aigateway"; assert aigw["caller"]=="aigw-runtime-key:agents"


def test_delegated_user_profile_and_scopes_are_separate_from_caller_application():
    module = load_module("delegated_audit_test", ROOT / "src" / "catalog-mcp" / "audit.py")
    headers = {
        "x-gw-user-oid": "synthetic-user", "x-gw-user-name": "Synthetic Operator",
        "x-gw-user-username": "operator@example.test", "x-gw-delegated-scopes": "Gateway.Access",
        "x-gw-agent-appid": "console-application", "x-gw-agent-oid": "synthetic-user",
    }
    record = module.build_audit_record(service="svc", tool="tools/list", operation="tools/list", decision="allowed", reason="ok", headers=headers, domain_profile="it-service-desk", latency_ms=1, status_code=200)
    assert record["identity_type"] == "delegated_user"
    assert record["human_principal"] == {"oid": "synthetic-user", "name": "Synthetic Operator", "username": "operator@example.test"}
    assert record["agent_principal"]["appid"] == "console-application"
    assert record["delegated_scopes"] == "Gateway.Access"
    headers.pop("x-gw-user-oid")
    application = module.build_audit_record(service="svc", tool="tools/list", operation="tools/list", decision="allowed", reason="ok", headers=headers, domain_profile="it-service-desk", latency_ms=1, status_code=200)
    assert application["human_principal"] is None and application["delegated_scopes"] is None
    assert application["identity_type"] == "application"
