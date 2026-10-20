
import json, re, pytest
from conftest import ROOT
KNOWN_TABLES={"ApiManagementGatewayLogs","ApiManagementGatewayLlmLog","ApiManagementGatewayMCPLog","ContainerAppConsoleLogs_CL","AppTraces","AzureActivity","AADServicePrincipalSignInLogs","AADManagedIdentitySignInLogs","AuditLogs","AzureDiagnostics"}
def test_kql_queries_when_present():
    query_dir=ROOT/"infra"/"monitoring"/"queries"; files=sorted(query_dir.glob("*.kql"))
    if not files: pytest.skip("infra/monitoring/queries KQL files are written by the infra agent")
    assert len(files)>=10
    for path in files:
        text=path.read_text(); assert text.lstrip().startswith("//"), f"{path.name} needs a header comment"
        assert set(re.findall(r"\b[A-Z][A-Za-z0-9_]+\b", text)) & KNOWN_TABLES, f"{path.name} should reference at least one known table"


def test_workbook_binds_all_saved_queries_instead_of_copying_them():
    workbook = json.loads((ROOT / "infra/monitoring/workbook.json").read_text())
    module = (ROOT / "infra/modules/workbook.bicep").read_text()
    bindings = dict(re.findall(r"'([^']+)': (?:replace\(|(?:tokenTrend\()?'\$\{)?loadTextContent\('\.\./monitoring/queries/([^']+)'\)", module))
    assert set(bindings.values()) == {p.name for p in (ROOT / "infra/monitoring/queries").glob("*.kql")}
    panels = {item["name"]: item["content"] for item in workbook["items"] if item["type"] == 3}
    assert set(bindings) <= set(panels)
    assert len(panels) == 17
    for name in bindings:
        assert panels[name]["query"] == "", "Saved KQL must come from its source file at deployment."
    assert "serializedData: string(workbookData)" in module
    assert "crossComponentResources:" in module and "logAnalyticsWorkspaceId" in module
    assert "| take 200" in module


def test_workbook_time_and_trace_parameters_are_complete():
    workbook = json.loads((ROOT / "infra/monitoring/workbook.json").read_text())
    parameter_items = [item for item in workbook["items"] if item["type"] == 9]
    parameters = {p["name"]: p for item in parameter_items for p in item["content"]["parameters"]}
    assert parameters["traceId"]["isRequired"] is False
    assert parameters["traceId"]["value"] == ""
    assert parameters["TimeRange"]["value"]["durationMs"] == 86400000
    for item in workbook["items"]:
        if item["type"] == 3:
            assert item["content"]["timeContextFromParameter"] == "TimeRange"
            references = re.findall(r"\{(\w+)(?::\w+)?\}", item["content"]["query"])
            assert set(references) <= set(parameters)
    module = (ROOT / "infra/modules/workbook.bicep").read_text()
    assert 'let traceId = "{traceId:escapejson}";' in module


def test_trace_query_keeps_apim_schema_and_audit_links():
    query = (ROOT / "infra/monitoring/queries/04-end-to-end-trace.kql").read_text()
    assert "DurationMs=todouble(TotalTime)" in query
    assert "LastErrorMessage" in query
    assert "CorrelationId in (GatewayIds)" in query
    assert 'tostring(audit.event) == "tool_audit"' in query
    assert "AppGenAIContent" in query
    assert "Properties=pack_all()" not in query
    assert 'declare query_parameters(traceId:string = "");' in query


def test_optional_export_queries_have_typed_empty_inputs():
    for number in ("07", "08"):
        path, = (ROOT / "infra/monitoring/queries").glob(f"{number}-*.kql")
        text = path.read_text()
        assert "union isfuzzy=true" in text
        assert "datatable(TimeGenerated:datetime" in text


def test_workbook_explains_evidence_limits_and_uses_real_schema():
    workbook = json.loads((ROOT / "infra/monitoring/workbook.json").read_text())
    panels = {item["name"]: item["content"] for item in workbook["items"] if item["type"] == 3}
    assert "Duration=todouble(TotalTime)" in panels["latency-5xx"]["query"]
    assert "AppGenAIContent" in panels["hosted-agent-content"]["query"]
    assert "Rows=count()" in panels["telemetry-coverage"]["query"]
    title = workbook["items"][0]["content"]["json"]
    assert "not proof" in title and "not sum" in title and "Privacy" in title
    tier = (ROOT / "infra/monitoring/queries/11-ai-gateway-tier-telemetry.kql").read_text()
    assert 'Gateway="mcp-resource-log"' in tier
    assert 'Gateway="aigateway-tier-mcp-log"' not in tier
    tokens = (ROOT / "infra/monitoring/queries/02-token-usage-by-agent-and-user.kql").read_text()
    assert 'by agent_name=coalesce(' in tokens
    assert 'by agent_appid=tostring(p["gen_ai.agent.name"])' not in tokens
    assert "ContainerRegistryRepositoryEvents" in panels["platform-audit"]["query"]


def test_workbook_preserves_explicit_token_visualizations():
    workbook = json.loads((ROOT / "infra/monitoring/workbook.json").read_text())
    panels = {item["name"]: item for item in workbook["items"] if item["type"] == 3}
    for name in ("gateway-token-trend", "agent-token-trend"):
        panel = panels[name]
        assert panel["customWidth"] == "50"
        content = panel["content"]
        assert content["visualization"] == "timechart"
        assert content["chartSettings"]["xAxis"] == "TimeGenerated"
        assert content["chartSettings"]["yAxis"] == ["Tokens"]
        assert content["chartSettings"]["group"] == "Series"
        assert content["chartSettings"]["showLegend"] is True
        assert "No " in content["noDataMessage"]
    module = (ROOT / "infra/modules/workbook.bicep").read_text()
    assert 'Gateway in ("apim-standard-v2", "aigateway-tier") and Surface == "llm"' in module
    assert 'Group=iff(Gateway == "aigateway-tier", "AI Gateway - Foundry-observed", "APIM v2")' in module
    assert 'Gateway startswith "hosted-agent:" and Surface == "chat"' in module
    assert 'Series=pack_array(strcat(Group, " / input"), strcat(Group, " / output"))' in module
    assert "Tokens=pack_array(InputTokens, OutputTokens)" in module
    assert "| mv-expand Series to typeof(string), Tokens to typeof(long)" in module
    assert "| make-series Tokens=sum(Tokens) default=0" in module
    assert "from {TimeRange:start} to {TimeRange:end} step {TimeRange:grain} by Series" in module
    assert "bin_at(TimeGenerated, {TimeRange:grain}, {TimeRange:start})" in module
    assert "| project TimeGenerated, Tokens, Series" in module
    assert "| top 2000" not in module


def test_workbook_charts_expand_typed_points_without_truncating_the_window():
    module = (ROOT / "infra/modules/workbook.bicep").read_text()
    trend = re.search(r"func tokenTrend.*?'''\n(.*?)\n'''", module, re.DOTALL).group(1)
    expand = "| mv-expand TimeGenerated to typeof(datetime), Tokens to typeof(long)"
    assert trend.index("| make-series") < trend.index("| take 200") < trend.index(expand)
    assert "| take" not in trend[trend.index(expand):]
    assert "| order by TimeGenerated asc, Series asc" in trend
    assert "endsWith(item.name, '-token-trend') ? savedQueries[item.name]" in module
    assert "| project TimeGenerated, Tokens, Series" in trend[trend.index(expand):]


def test_workbook_uses_datetime_parameter_expressions_without_rewrapping():
    module = (ROOT / "infra/modules/workbook.bicep").read_text()
    assert "datetime({TimeRange:start})" not in module
    assert "datetime({TimeRange:end})" not in module
    expanded = module
    for parameter, value in {
        "start": "datetime(2026-10-15T17:35:00Z)",
        "end": "datetime(2026-10-16T17:35:00Z)",
        "grain": "30m",
    }.items():
        expanded = expanded.replace("{TimeRange:" + parameter + "}", value)
    assert "datetime(datetime(" not in expanded
    assert "bin_at(TimeGenerated, 30m, datetime(2026-10-15T17:35:00Z))" in expanded
    assert "from datetime(2026-10-15T17:35:00Z) to datetime(2026-10-16T17:35:00Z) step 30m" in expanded


def test_workbook_sections_and_trace_input_follow_panel_scope():
    workbook = json.loads((ROOT / "infra/monitoring/workbook.json").read_text())
    items = {item["name"]: item for item in workbook["items"]}
    names = [item["name"] for item in workbook["items"]]
    assert len(names) == len(set(names))
    headers = [
        "overview-header", "token-details-header", "activity-header", "security-header",
        "trace-guidance", "message-sample-header", "coverage-header",
    ]
    assert [names.index(name) for name in headers] == sorted(names.index(name) for name in headers)
    assert names.index("overview-header") < names.index("gateway-token-trend") < names.index("token-details-header")
    assert names.index("overview-header") < names.index("agent-token-trend") < names.index("token-details-header")
    assert [p["name"] for p in items["parameters"]["content"]["parameters"]] == ["TimeRange"]
    assert [p["name"] for p in items["trace-parameters"]["content"]["parameters"]] == ["traceId"]
    assert names.index("trace-guidance") < names.index("trace-parameters") < names.index("trace-lookup")
    assert names.index("trace-lookup") < names.index("hosted-agent-content") < names.index("message-sample-header")
    assert "only" in items["trace-guidance"]["content"]["json"]
    assert "time range" in items["message-sample-header"]["content"]["json"]


def test_workbook_scopes_sources_before_aggregation_and_limits():
    module = (ROOT / "infra/modules/workbook.bicep").read_text()
    assert 'let ${tableName} = ${tableName} | where TimeGenerated {TimeRange:query};' in module
    assert "query: scopeQueryToTimeRange(" in module
    assert re.search(r": item\.content\.query,\s+sourceTables,\s+aigwPrincipalId\s+\)", module)
    table_list = re.search(r"var sourceTables = \[(.*?)\]", module, re.DOTALL).group(1)
    tables = set(re.findall(r"'([^']+)'", table_list))
    assert tables == KNOWN_TABLES | {
        "AppRequests", "AppDependencies", "AppGenAIContent",
        "ContainerRegistryLoginEvents", "ContainerRegistryRepositoryEvents",
    }
    workbook = json.loads((ROOT / "infra/monitoring/workbook.json").read_text())
    overview = next(item for item in workbook["items"] if item["name"] == "overview-header")
    assert "{TimeRange:label}" in overview["content"]["json"]


def test_monitoring_documentation_quotes_current_saved_queries():
    doc = (ROOT / "docs/09-monitoring-and-audit.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```kusto\n(.*?)```", doc, re.DOTALL)
    files = sorted((ROOT / "infra/monitoring/queries").glob("*.kql"))
    assert len(blocks) == len(files) == 11
    for block, path in zip(blocks, files):
        assert block.rstrip() == path.read_text().rstrip(), path.name


def test_apim_request_counts_ignore_split_llm_log_records():
    query02 = (ROOT / "infra/monitoring/queries/02-token-usage-by-agent-and-user.kql").read_text()
    apim02 = query02.split("let ApimLlmLog =", 1)[1].split("let TierRequests =", 1)[0]
    key = "by ResourceId=tostring(_ResourceId), CorrelationId"
    assert key in apim02
    assert "ModelName=take_anyif(ModelName, isnotempty(ModelName))" in apim02
    assert "Requests=sum(Requests)" not in apim02
    assert apim02.index(key) < apim02.index("Requests=count()")
    query11 = (ROOT / "infra/monitoring/queries/11-ai-gateway-tier-telemetry.kql").read_text()
    apim11 = query11.split("let StandardV2 =", 1)[1].split("let AgentSpans =", 1)[0]
    assert apim11.index(key) < apim11.index("Requests=count()")
    assert "ModelName=take_anyif(ModelName, isnotempty(ModelName))" in apim11
    assert "Failed=long(null)" in apim11
    assert "InputTokens=sum(tolong(PromptTokens))" in apim11
    assert "OutputTokens=sum(tolong(CompletionTokens))" in apim11


def test_tier_tokens_use_identity_attributed_deduplicated_backend_counters():
    for number in ("02", "11"):
        path, = (ROOT / "infra/monitoring/queries").glob(f"{number}-*.kql")
        text = path.read_text()
        assert 'let aigwPrincipalId = "";' in text
        assert 'Category == "RequestResponse"' in text
        assert 'isnotempty(aigwPrincipalId) and tostring(p.callerObjectId) =~ aigwPrincipalId' in text
        assert "by BackendResourceId, BackendRequestId" in text
        assert "arg_max(TimeGenerated," in text
        assert "isnotnull(" in text
        assert "p.promptTokens" in text and "p.completionTokens" in text
        assert 'm["gen_ai.usage.input_tokens"]' not in text
    tier = (ROOT / "infra/monitoring/queries/11-ai-gateway-tier-telemetry.kql").read_text()
    assert '"llm-request"' in tier
    assert 'TokenSource="not-reported-in-request-log"' in tier
    assert "InputTokens=long(null), OutputTokens=long(null)" in tier
    module = (ROOT / "infra/modules/workbook.bicep").read_text()
    assert "AI Gateway - Foundry-observed" in module
    assert "replace(query, 'let aigwPrincipalId" in module
    querypack = (ROOT / "infra/modules/querypack.bicep").read_text()
    assert "body: replace(query.body, 'let aigwPrincipalId" in querypack
    main = (ROOT / "infra/main.bicep").read_text()
    assert main.count("aigwPrincipalId: aigwPrincipalId") == 3


def test_audit_cli_binds_only_valid_gateway_identity():
    from conftest import load_module
    module = load_module("audit_queries", ROOT / "scripts/run_audit_queries.py")
    query = 'let aigwPrincipalId = "";'
    principal_id = "11111111-2222-3333-4444-555555555555"
    assert module.bind_gateway_identity(query, principal_id) == f'let aigwPrincipalId = "{principal_id}";'
    with pytest.raises(SystemExit, match="principal GUID"):
        module.bind_gateway_identity(query, '"; union AppRequests')
