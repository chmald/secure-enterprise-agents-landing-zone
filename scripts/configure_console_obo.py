from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
AZ = "az.cmd" if os.name == "nt" else "az"
CURL = "curl.exe" if os.name == "nt" else "curl"


def command(arguments: list[str]) -> str:
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{arguments[0]} {arguments[1]} failed (exit {result.returncode}); no credential output was printed.")
    return result.stdout.strip()


def environment_value(environment: str, name: str, required: bool = True) -> str:
    value = os.environ.get(name)
    if value:
        return value
    result = subprocess.run(["azd", "env", "get-value", name, "--environment", environment], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        error = (result.stdout + result.stderr).lower()
        if not required and ("not found" in error or "does not exist" in error):
            return ""
        raise RuntimeError(f"Cannot read azd setting {name}; no settings or credentials were printed.")
    value = result.stdout.strip().strip('"')
    if required and not value:
        raise RuntimeError(f"{name} is required.")
    return value


def save_secret(environment: str, name: str, value: str) -> None:
    path = ROOT / ".azure" / environment / ".env"
    if not path.is_file():
        raise RuntimeError("The existing ignored azd environment file is required to save the credential.")
    command(["git", "-C", str(ROOT), "check-ignore", "--quiet", str(path)])
    before = path.stat().st_mtime_ns
    text = path.read_text(encoding="utf-8")
    pattern = rf"(?m)^{re.escape(name)}=.*$"
    if len(re.findall(pattern, text)) > 1:
        raise RuntimeError(f"Duplicate {name} settings; refusing to rewrite the environment.")
    entry = name + "=" + json.dumps(value)
    updated = re.sub(pattern, lambda _: entry, text) if re.search(pattern, text) else text.rstrip("\n") + "\n" + entry + "\n"
    temporary = path.with_name(".env.obo-credential.tmp")
    try:
        temporary.write_text(updated, encoding="utf-8")
        if path.stat().st_mtime_ns != before:
            raise RuntimeError("The azd environment changed concurrently; the credential was not written over it.")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def ensure_scope(api: dict, value: str, title: str) -> tuple[dict, str]:
    result = copy.deepcopy(api)
    scopes = result.setdefault("oauth2PermissionScopes", [])
    existing = next((scope for scope in scopes if scope["value"] == value), None)
    if existing:
        if not existing.get("isEnabled"):
            raise RuntimeError(f"The existing {value} scope is disabled; review it rather than silently re-enabling it.")
        return result, existing["id"]
    scope_id = str(uuid.uuid4())
    scopes.append({
        "id": scope_id, "value": value, "type": "User", "isEnabled": True,
        "adminConsentDisplayName": title, "adminConsentDescription": "Access the governed demo as a signed-in user. Business and record-level authorization require separate validation.",
        "userConsentDisplayName": title, "userConsentDescription": "Access this non-production demo as you. The identity probe is read-only; this permission is not a per-record entitlement.",
    })
    return result, scope_id


def preauthorize(api: dict, client_id: str, scope_id: str) -> dict:
    result = copy.deepcopy(api)
    clients = result.setdefault("preAuthorizedApplications", [])
    existing = next((client for client in clients if client["appId"] == client_id), None)
    if existing is None:
        clients.append({"appId": client_id, "delegatedPermissionIds": [scope_id]})
    elif scope_id not in existing["delegatedPermissionIds"]:
        existing["delegatedPermissionIds"].append(scope_id)
    return result


def require_scope(resources: list[dict], resource_id: str, scope_id: str) -> list[dict]:
    result = copy.deepcopy(resources)
    resource = next((item for item in result if item["resourceAppId"] == resource_id), None)
    if resource is None:
        result.append({"resourceAppId": resource_id, "resourceAccess": [{"id": scope_id, "type": "Scope"}]})
    elif not any(item["id"] == scope_id and item["type"] == "Scope" for item in resource["resourceAccess"]):
        resource["resourceAccess"].append({"id": scope_id, "type": "Scope"})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure only owned Entra apps for the optional console-to-APIM OBO demo; never provisions Azure resources.")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--apply", action="store_true", help="Create/update the narrowly scoped demo apps and save the new secret only to ignored azd state.")
    parser.add_argument("--redirect-only", action="store_true", help="Update only the interactive client's callback after provisioning.")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,19}", args.environment):
        raise RuntimeError("Use the existing lowercase azd environment name.")
    tenant = environment_value(args.environment, "AZURE_TENANT_ID")
    subscription = environment_value(args.environment, "AZURE_SUBSCRIPTION_ID")
    context = json.loads(command([AZ, "account", "show", "-o", "json"]))
    if context["tenantId"] != tenant or context["id"] != subscription:
        raise RuntimeError("Azure CLI tenant/subscription differs from the intended azd environment.")
    user = command([AZ, "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"])
    if user != environment_value(args.environment, "DEMO_CONSOLE_ALLOWED_USER_ID"):
        raise RuntimeError("Sign in as the allowed human deployer; no implicit ownership transfer is allowed.")
    token = command([AZ, "account", "get-access-token", "--tenant", tenant, "--resource", "https://graph.microsoft.com", "--query", "accessToken", "-o", "tsv"])

    def graph(path: str, method: str = "GET", payload: dict | None = None) -> dict:
        config = [
            "silent", "show-error", "ipv4", "connect-timeout = 10", "max-time = 35",
            "request = " + json.dumps(method), "url = " + json.dumps("https://graph.microsoft.com/v1.0" + quote(path, safe="/?=&$'(),:")),
            "header = " + json.dumps("Authorization: Bearer " + token), 'write-out = "\\n%{http_code}"',
        ]
        if payload is not None:
            config += ['header = "Content-Type: application/json"', "data = " + json.dumps(json.dumps(payload))]
        result = subprocess.run([CURL, "--config", "-"], input="\n".join(config), capture_output=True, text=True, timeout=40, check=True)
        text, status = result.stdout.rsplit("\n", 1)
        value = json.loads(text) if text else {}
        if not 200 <= int(status) < 300 or value.get("error"):
            code = value.get("error", {}).get("code", "unknown")
            message = str(value.get("error", {}).get("message", "No error detail returned.")).replace(token, "[redacted]")
            message = re.sub(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "[application/scope ID]", message)
            raise RuntimeError(f"Owned-app Graph {method} returned HTTP {status}, code={code}: {message}")
        return value

    def owned(client_id: str) -> dict:
        client_id = str(uuid.UUID(client_id))
        app = graph(f"/applications(appId='{client_id}')")
        if app["signInAudience"] != "AzureADMyOrg":
            raise RuntimeError("All OBO demo applications must be single-tenant.")
        owners = graph(f"/applications/{app['id']}/owners?$select=id")["value"]
        if not any(owner["id"] == user for owner in owners):
            raise RuntimeError("The deployer must own each demo registration; other applications are not modified.")
        return app

    console_id = environment_value(args.environment, "DEMO_CONSOLE_CLIENT_ID")
    gateway_id = environment_value(args.environment, "GATEWAY_APP_CLIENT_ID")
    console = owned(console_id)
    gateway = owned(gateway_id)
    interactive_id = environment_value(args.environment, "DEMO_OBO_CLIENT_ID", required=False)
    origin = environment_value(args.environment, "DEMO_CONSOLE_URL", required=False).rstrip("/")
    if origin and not re.fullmatch(r"https://[A-Za-z0-9.-]+", origin):
        raise RuntimeError("DEMO_CONSOLE_URL must be the HTTPS console origin.")
    callback = origin + "/api/identity/obo/callback" if origin else ""
    if not args.apply:
        print("Plan: one auxiliary single-tenant sign-in client; Console.Access and Gateway.Access; only the required demo client preauthorizations; optional operator profile claims. No tenant-wide consent grants or Azure provisioning.")
        return
    if not interactive_id:
        if args.redirect_only:
            raise RuntimeError("No interactive OBO registration exists.")
        created = json.loads(command([AZ, "ad", "app", "create", "--display-name", "console-obo-" + args.environment, "--sign-in-audience", "AzureADMyOrg", "-o", "json"]))
        interactive_id = created["appId"]
        command(["azd", "env", "set", "DEMO_OBO_CLIENT_ID", interactive_id, "--environment", args.environment])
    interactive = owned(interactive_id)
    if callback:
        web = copy.deepcopy(interactive.get("web") or {})
        redirects = web.setdefault("redirectUris", [])
        if callback not in redirects:
            redirects.append(callback)
            graph(f"/applications/{interactive['id']}", "PATCH", {"web": web})
    if args.redirect_only:
        if not callback:
            raise RuntimeError("The deployed console URL is required to update the callback.")
        print("Updated the OBO interactive client's exact callback; other application settings preserved.")
        return
    api_console, console_scope = ensure_scope(console.get("api") or {}, "Console.Access", "Access the demo console as you")
    api_gateway, gateway_scope = ensure_scope(gateway.get("api") or {}, "Gateway.Access", "Access the demo gateway as you")
    api_console["requestedAccessTokenVersion"] = 2
    api_gateway["requestedAccessTokenVersion"] = 2
    identifiers = list(console.get("identifierUris") or [])
    if "api://" + console_id not in identifiers:
        identifiers.append("api://" + console_id)
    graph(f"/applications/{console['id']}", "PATCH", {
        "identifierUris": identifiers, "api": api_console,
    })
    optional = copy.deepcopy(gateway.get("optionalClaims") or {})
    access_claims = optional.setdefault("accessToken", [])
    for name in ("upn", "email"):
        if not any(claim["name"] == name for claim in access_claims):
            access_claims.append({"name": name, "essential": False, "additionalProperties": []})
    gateway_identifiers = list(gateway.get("identifierUris") or [])
    if "api://" + gateway_id not in gateway_identifiers:
        gateway_identifiers.append("api://" + gateway_id)
    graph(f"/applications/{gateway['id']}", "PATCH", {"identifierUris": gateway_identifiers, "api": api_gateway, "optionalClaims": optional})
    # Entra resolves preauthorizations against persisted scopes, not scopes in the same PATCH.
    console = owned(console_id)
    gateway = owned(gateway_id)
    api_console, console_scope = ensure_scope(console.get("api") or {}, "Console.Access", "Access the demo console as you")
    api_gateway, gateway_scope = ensure_scope(gateway.get("api") or {}, "Gateway.Access", "Access the demo gateway as you")
    graph(f"/applications/{console['id']}", "PATCH", {
        "api": preauthorize(api_console, interactive_id, console_scope),
        "requiredResourceAccess": require_scope(console.get("requiredResourceAccess") or [], gateway_id, gateway_scope),
    })
    graph(f"/applications/{gateway['id']}", "PATCH", {"api": preauthorize(api_gateway, console_id, gateway_scope)})
    graph(f"/applications/{interactive['id']}", "PATCH", {
        "requiredResourceAccess": require_scope(interactive.get("requiredResourceAccess") or [], console_id, console_scope),
    })
    for client_id in (interactive_id, console_id, gateway_id):
        service_principals = graph(f"/servicePrincipals?$filter=appId eq '{client_id}'&$select=id")["value"]
        if not service_principals:
            graph("/servicePrincipals", "POST", {"appId": client_id})
    if not environment_value(args.environment, "DEMO_OBO_CLIENT_SECRET", required=False):
        expires = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat().replace("+00:00", "Z")
        credential = graph(f"/applications/{interactive['id']}/addPassword", "POST", {"passwordCredential": {"displayName": "demo-console-obo", "endDateTime": expires}})
        secret = credential.get("secretText")
        if not isinstance(secret, str) or not secret:
            raise RuntimeError("Entra did not return the new interactive-client credential.")
        save_secret(args.environment, "DEMO_OBO_CLIENT_SECRET", secret)
    command(["azd", "env", "set", "ENABLE_DEMO_OBO", "true", "--environment", args.environment])
    print("Configured owned OBO apps/scopes and saved the auxiliary credential only to ignored azd state. No tenant-wide OAuth grant or Azure resource provisioning was performed.")
    print("Deploy the narrow console/policy/audit updates, then complete real user sign-in. Configuration alone is not an OBO/audit pass.")


if __name__ == "__main__":
    main()
