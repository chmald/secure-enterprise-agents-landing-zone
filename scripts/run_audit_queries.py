
from __future__ import annotations
import argparse, os, uuid
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from azure.core.credentials import AccessToken
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
ROOT=Path(__file__).resolve().parents[1]; QUERY_DIR=ROOT/"infra"/"monitoring"/"queries"
def load_ids(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
def bind_gateway_identity(query: str, principal_id: str) -> str:
    try:
        principal_id = str(uuid.UUID(principal_id))
    except ValueError:
        raise SystemExit("aigwPrincipalId / AIGW_PRINCIPAL_ID must be a managed-identity principal GUID") from None
    return query.replace('let aigwPrincipalId = "";', f'let aigwPrincipalId = "{principal_id}";')
class AzCliCredential:
    def get_token(self, *scopes, **kwargs):
        scope=scopes[0] if scopes else "https://api.loganalytics.io/.default"
        resource=scope[:-len("/.default")] if scope.endswith("/.default") else scope
        tenant=os.environ.get("AZURE_TENANT_ID")
        token=subprocess.run(["az","account","get-access-token",*(["--tenant",tenant] if tenant else []),"--resource",resource,"-o","json"],check=True,capture_output=True,text=True)
        data=json.loads(token.stdout)
        return AccessToken(data["accessToken"], int(time.time()) + 3000)
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p=argparse.ArgumentParser(); p.add_argument("--ids",default=str(ROOT/"demo-ids.local.json")); p.add_argument("--workspace-id"); p.add_argument("--query",default="01"); p.add_argument("--trace-id"); a=p.parse_args(); ids=load_ids(Path(a.ids)); wid=a.workspace_id or ids.get("logAnalyticsCustomerId") or os.environ.get("LOG_ANALYTICS_CUSTOMER_ID")
    if not wid: raise SystemExit("LOG_ANALYTICS_CUSTOMER_ID is required")
    files=sorted(QUERY_DIR.glob("*.kql")); files=files if a.query=="all" else [x for x in files if x.name.startswith(f"{a.query}-")]
    if not files: raise SystemExit(f"No KQL files found for query {a.query} under {QUERY_DIR}")
    try:
        DefaultAzureCredential().get_token("https://api.loganalytics.io/.default")
        credential=DefaultAzureCredential()
    except Exception:
        credential=AzCliCredential()
    client=LogsQueryClient(credential)
    for path in files:
        query=path.read_text();
        if path.name.startswith(("02-", "11-")):
            principal_id = ids.get("aigwPrincipalId") or os.environ.get("AIGW_PRINCIPAL_ID")
            if principal_id:
                query = bind_gateway_identity(query, principal_id)
            else:
                print("WARNING: AI Gateway token attribution unavailable; populate aigwPrincipalId / AIGW_PRINCIPAL_ID.", file=sys.stderr)
        if path.name.startswith("04-") and a.trace_id:
            if not re.fullmatch(r"[0-9A-Za-z-]+", a.trace_id): raise SystemExit("--trace-id must be alphanumeric/hyphen")
            query=query.replace('traceId:string = ""', f'traceId:string = "{a.trace_id}"')
        print(f"\n## {path.name}"); result=client.query_workspace(wid, query, timespan=None)
        for table in getattr(result,"tables",[]) or []:
            print(" | ".join(table.columns)); [print(" | ".join(str(c) for c in row)) for row in table.rows]
    return 0
if __name__=="__main__": raise SystemExit(main())
