
import json, os, signal, uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from audit import AuditTimer, build_audit_record, configure_azure_monitor_if_available, configure_logging, emit_audit_record

PROTOCOL_VERSION="2025-06-18"; SERVICE_NAME="records-api"; DEFAULT_PROFILE="manufacturing-field-ops"; SESSION_ID_HEADER="mcp-session-id"; ROOT=Path(__file__).resolve().parents[2]
RecordStatus=Literal["open","in_progress","completed","cancelled"]; RecordPriority=Literal["low","medium","high","critical"]

def load_profile() -> dict[str, Any]:
    name=os.environ.get("DOMAIN_PROFILE") or DEFAULT_PROFILE; path=ROOT/"config"/"profiles"/f"{name}.json"
    if not path.exists(): raise RuntimeError(f"Profile not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
PROFILE=load_profile(); LABELS=PROFILE["labels"]; configure_logging(); configure_azure_monitor_if_available()

class ItemRequirement(BaseModel): item_id: str; quantity: int = Field(..., ge=1)
class Record(BaseModel):
    id: str; title: str; description: str; status: Literal["open","in_progress","completed","cancelled"]="open"; priority: Literal["low","medium","high","critical"]; assigned_to: str; location: str; items_required: list[ItemRequirement]=Field(default_factory=list); created_at: datetime; updated_at: datetime; due_date: datetime
class RecordCreate(BaseModel):
    title: str; description: str; status: Literal["open","in_progress","completed","cancelled"]="open"; priority: Literal["low","medium","high","critical"]; assigned_to: str; location: str; items_required: list[ItemRequirement]=Field(default_factory=list); due_date: datetime
    model_config={"extra":"forbid"}
class RecordUpdate(BaseModel):
    title: str|None=None; description: str|None=None; status: Literal["open","in_progress","completed","cancelled"]|None=None; priority: Literal["low","medium","high","critical"]|None=None; assigned_to: str|None=None; location: str|None=None; items_required: list[ItemRequirement]|None=None; due_date: datetime|None=None
    model_config={"extra":"forbid"}

def data_path() -> Path: return ROOT/PROFILE["seedData"]["records"]
def load_records() -> list[Record]: return [Record.model_validate(r) for r in json.loads(data_path().read_text(encoding="utf-8"))]

summaries=PROFILE["recordsTools"]; app=FastAPI(title=f"{PROFILE['displayName']} Records API",version="1.0.0",openapi_version="3.1.0"); app.state.records=load_records()

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    with AuditTimer() as timer: response: Response = await call_next(request)
    route=request.scope.get("route"); route_name=route.name if route else request.url.path
    emit_audit_record(build_audit_record(service=SERVICE_NAME, tool=str(route_name), operation=request.method, decision="allowed" if response.status_code<400 else "denied", reason="http_request", headers=dict(request.headers), domain_profile=PROFILE["profileName"], latency_ms=timer.elapsed_ms, status_code=response.status_code))
    return response

def records() -> list[Record]: return app.state.records

def find_record(record_id: str) -> tuple[int, Record]:
    for i,r in enumerate(records()):
        if r.id.upper()==record_id.upper(): return i,r
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{LABELS['record'].title()} not found")

def next_record_id() -> str:
    existing=[r.id for r in records()]; prefix=existing[0].split("-")[0] if existing and "-" in existing[0] else "REC"; nums=[int(v.split("-")[1]) for v in existing if "-" in v and v.split("-")[1].isdigit()]
    return f"{prefix}-{max(nums, default=0)+1:03d}"

def tool_definitions() -> list[dict[str, Any]]:
    d=PROFILE["recordsTools"]
    return [
      {"name":"list_records","description":d["list_records"],"inputSchema":{"type":"object","properties":{"status":{"type":"string"},"priority":{"type":"string"},"assigned_to":{"type":"string"},"location":{"type":"string"}}}},
      {"name":"get_record","description":d["get_record"],"inputSchema":{"type":"object","properties":{"record_id":{"type":"string"}},"required":["record_id"]}},
      {"name":"create_record","description":d["create_record"],"inputSchema":{"type":"object","properties":{"title":{"type":"string"},"description":{"type":"string"},"priority":{"type":"string"},"assigned_to":{"type":"string"},"location":{"type":"string"},"items_required":{"type":"array"},"due_date":{"type":"string"}},"required":["title","description","priority","assigned_to","location","due_date"]}},
      {"name":"update_record","description":d["update_record"],"inputSchema":{"type":"object","properties":{"record_id":{"type":"string"},"title":{"type":"string"},"description":{"type":"string"},"status":{"type":"string"},"priority":{"type":"string"},"assigned_to":{"type":"string"},"location":{"type":"string"},"items_required":{"type":"array"},"due_date":{"type":"string"}},"required":["record_id"]}},
    ]

def jsonrpc_result(i: Any, result: Any) -> dict[str, Any]: return {"jsonrpc":"2.0","id":i,"result":result}
def jsonrpc_error(i: Any, code: int, message: str) -> dict[str, Any]: return {"jsonrpc":"2.0","id":i,"error":{"code":code,"message":message}}

def record_to_json(record: Record) -> dict[str, Any]:
    return record.model_dump(mode="json")

def call_tool(name: str, args: dict[str, Any]) -> Any:
    if name=="list_records":
        return [record_to_json(r) for r in list_records(args.get("status"), args.get("priority"), args.get("assigned_to"), args.get("location"))]
    if name=="get_record":
        return record_to_json(get_record(str(args.get("record_id") or args.get("id") or "")))
    if name=="create_record":
        return record_to_json(create_record(RecordCreate.model_validate(args)))
    if name=="update_record":
        record_id=str(args.get("record_id") or args.get("id") or "")
        payload={k:v for k,v in args.items() if k not in ("record_id","id")}
        return record_to_json(update_record(record_id, RecordUpdate.model_validate(payload)))
    raise ValueError(f"Unknown tool: {name}")

@app.get("/healthz")
def healthz(): return {"status":"ok","service":SERVICE_NAME,"domain_profile":PROFILE["profileName"],"records_loaded":len(records())}

@app.get("/records/", response_model=list[Record], include_in_schema=False)
@app.get("/records", response_model=list[Record], operation_id="list_records", summary=summaries["list_records"])
def list_records(status_filter: Literal["open","in_progress","completed","cancelled"]|None=Query(default=None, alias="status"), priority: Literal["low","medium","high","critical"]|None=None, assigned_to: str|None=None, location: str|None=None):
    result=records()
    if status_filter: result=[r for r in result if r.status==status_filter]
    if priority: result=[r for r in result if r.priority==priority]
    if assigned_to: result=[r for r in result if assigned_to.lower() in r.assigned_to.lower()]
    if location: result=[r for r in result if location.lower() in r.location.lower()]
    return result

@app.get("/records/{record_id}", response_model=Record, operation_id="get_record", summary=summaries["get_record"])
def get_record(record_id: str): return find_record(record_id)[1]

@app.post("/records/", response_model=Record, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@app.post("/records", response_model=Record, status_code=status.HTTP_201_CREATED, operation_id="create_record", summary=summaries["create_record"])
def create_record(payload: RecordCreate):
    now=datetime.now(UTC); record=Record(id=next_record_id(), created_at=now, updated_at=now, **payload.model_dump()); records().append(record); return record

@app.patch("/records/{record_id}", response_model=Record, operation_id="update_record", summary=summaries["update_record"])
def update_record(record_id: str, payload: RecordUpdate):
    i,existing=find_record(record_id); updated=existing.model_copy(update={**payload.model_dump(exclude_unset=True),"updated_at":datetime.now(UTC)}); records()[i]=updated; return updated

@app.post("/mcp")
async def mcp(request: Request) -> Response:
    headers=dict(request.headers); message={}; tool="unknown"; decision="allowed"; reason="ok"; status_code=200
    with AuditTimer() as timer:
      try: message=await request.json()
      except Exception as exc:
        payload=jsonrpc_error(None,-32700,f"Parse error: {exc}"); tool="parse"; decision="denied"; reason="invalid_json"
      else:
        method=message.get("method") if isinstance(message,dict) else None; request_id=message.get("id") if isinstance(message,dict) else None; tool=method or "unknown"
        if not isinstance(message,dict) or message.get("jsonrpc")!="2.0": payload=jsonrpc_error(request_id,-32602,"Invalid JSON-RPC 2.0 request envelope"); decision="denied"; reason="invalid_envelope"
        elif method=="initialize": payload=jsonrpc_result(request_id,{"protocolVersion":PROTOCOL_VERSION,"capabilities":{"tools":{}},"serverInfo":{"name":SERVICE_NAME,"version":"1.0.0"}})
        elif method=="notifications/initialized": return Response(status_code=status.HTTP_202_ACCEPTED)
        elif method=="tools/list": payload=jsonrpc_result(request_id,{"tools":tool_definitions()})
        elif method=="tools/call":
          params=message.get("params") or {}; name=params.get("name"); args=params.get("arguments") or {}; tool=str(name)
          try:
            result=call_tool(str(name), args); payload=jsonrpc_result(request_id,{"content":[{"type":"text","text":json.dumps(result)}],"structuredContent":result,"isError":False})
          except Exception as exc:
            payload=jsonrpc_error(request_id,-32603,str(exc)); decision="denied"; reason="tool_error"
        else: payload=jsonrpc_error(request_id,-32601,f"Method not found: {method}"); decision="denied"; reason="method_not_found"
    emit_audit_record(build_audit_record(service=SERVICE_NAME, tool=tool, operation=str(message.get("method","unknown")) if isinstance(message,dict) else "unknown", decision=decision, reason=reason, headers=headers, domain_profile=PROFILE["profileName"], latency_ms=timer.elapsed_ms, status_code=status_code))
    response=JSONResponse(payload, status_code=status_code)
    if isinstance(message,dict) and message.get("method")=="initialize": response.headers[SESSION_ID_HEADER]=uuid.uuid4().hex
    return response

if __name__=="__main__":
    port=int(os.environ.get("PORT","8080")); config=uvicorn.Config(app,host="0.0.0.0",port=port,log_level="info"); server=uvicorn.Server(config); signal.signal(signal.SIGTERM, lambda *_: setattr(server,"should_exit",True)); server.run()
