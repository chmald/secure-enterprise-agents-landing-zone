from __future__ import annotations

import argparse
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

import httpx
from azure.identity import DefaultAzureCredential

ROOT = Path(__file__).resolve().parents[1]


def load_ids(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"workload": {"domainProfile": "manufacturing-field-ops", "profilePath": "config/profiles/manufacturing-field-ops.json"}}


def print_table(rows: list[dict[str, str]]) -> None:
    widths = {key: max(len(key), *(len(row[key]) for row in rows)) for key in rows[0]}
    print(" | ".join(key.ljust(widths[key]) for key in rows[0]))
    print(" | ".join("-" * widths[key] for key in rows[0]))
    for row in rows:
        print(" | ".join(row[key].ljust(widths[key]) for key in row))


def traceparent() -> str:
    return f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"


def env_agent_endpoint(agent: str, ids: dict[str, Any]) -> str | None:
    key = "agentMafResponsesEndpoint" if agent == "maf" else "agentLanggraphResponsesEndpoint"
    env_name = "AGENT_AGENT_MAF_RESPONSES_ENDPOINT" if agent == "maf" else "AGENT_AGENT_LANGGRAPH_RESPONSES_ENDPOINT"
    return os.environ.get(env_name) or ids.get(key)


def build_responses_endpoint(project_endpoint: str, agent: str) -> str:
    agent_name = "agent-maf" if agent == "maf" else "agent-langgraph"
    return f"{project_endpoint.rstrip('/')}/agents/{agent_name}/endpoint/protocols/openai/responses?api-version=v1"


def ai_token() -> str:
    try:
        return DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
    except Exception:
        tenant = os.environ.get("AZURE_TENANT_ID")
        result = subprocess.run(
            ["az", "account", "get-access-token", *(["--tenant", tenant] if tenant else []), "--resource", "https://ai.azure.com", "--query", "accessToken", "-o", "tsv"],
            check=True,
            capture_output=True,
            text=True,
        )
        token = result.stdout.strip()
        if not token:
            raise RuntimeError("az returned an empty token for https://ai.azure.com")
        return token


def invoke_agent(agent: str, ids: dict[str, Any], prompt: str) -> tuple[bool, str]:
    endpoint = env_agent_endpoint(agent, ids)
    if not endpoint:
        project_endpoint = ids.get("foundryProjectEndpoint") or os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
        if not project_endpoint:
            return False, "missing hosted agent endpoint or foundryProjectEndpoint"
        endpoint = build_responses_endpoint(project_endpoint, agent)
    token = ai_token()
    tp = traceparent()
    response = httpx.post(endpoint, headers={"Authorization": f"Bearer {token}", "traceparent": tp, "Content-Type": "application/json"}, json={"input": prompt, "stream": False}, timeout=90)
    detail = f"HTTP {response.status_code}; outgoing trace_id={tp.split('-')[1]} (verify propagation separately)"
    try:
        payload = response.json()
    except ValueError:
        return False, detail + "; response was not JSON"
    completed = (
        response.is_success and isinstance(payload, dict) and not payload.get("error")
        and payload.get("status") == "completed" and isinstance(payload.get("output"), list)
    )
    return completed, detail + ("; completed Responses payload" if completed else "; response did not complete successfully")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default=str(ROOT / "demo-ids.local.json"))
    parser.add_argument("--dry-run", action="store_true", help="Print PLAN rows only; never a live evidence pass.")
    parser.add_argument("--step", help="Run one walkthrough step such as S1, or 'smoke' for the readiness smoke step.")
    parser.add_argument("--agent", choices=["maf", "langgraph", "both"], default="maf")
    parser.add_argument("--gateway", choices=["apimv2", "aigateway"], default="apimv2", help="Expected route label only; does not switch deployed hosted agents.")
    args = parser.parse_args()

    ids = load_ids(Path(args.ids))
    profile_path = ids.get("workload", {}).get("profilePath", "config/profiles/manufacturing-field-ops.json")
    profile = json.loads((ROOT / profile_path).read_text(encoding="utf-8"))
    requested = (args.step or "").lower()
    steps = [step for step in profile["walkthrough"] if not requested or step["step"].lower() == requested or (requested == "smoke" and step["step"] == "S1")]
    if not steps:
        raise SystemExit(f"No walkthrough step matched {args.step!r}")

    agents = ["maf", "langgraph"] if args.agent == "both" else [args.agent]
    rows: list[dict[str, str]] = []
    for agent in agents:
        for step in steps:
            result = "PLAN" if args.dry_run else "NOT_RUN"
            detail = "Proposed check, not executed: " + step["assertion"]
            if not args.dry_run and step["step"] == "S1":
                ok, detail = invoke_agent(agent, ids, step["prompt"])
                result = "PASS" if ok else "FAIL"
            elif not args.dry_run:
                detail = f"No live {step['step']} check is implemented in this script; use the browser workflow and inspect its evidence."
            rows.append({"Agent": agent, "Expected gateway": args.gateway, "Step": step["step"], "Segment": step["segment"], "Expected tool": str(step.get("expectedTool") or "n/a"), "Result": result, "Check": detail})
    print_table(rows)
    print("The expected gateway is a label, not live routing discovery. Completed responses do not prove tool use, readiness or end-to-end traces.")
    if args.dry_run:
        return 0
    if any(row["Result"] == "FAIL" for row in rows):
        return 1
    return 2 if any(row["Result"] == "NOT_RUN" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
