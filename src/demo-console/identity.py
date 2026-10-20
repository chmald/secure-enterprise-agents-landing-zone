from __future__ import annotations

import base64
import binascii
import json
import logging
import re
import secrets
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

import msal
import requests

LOG = logging.getLogger("demo_console.identity")
COOKIE_NAME = "__Host-demo-obo"
FLOW_TTL = 600
RESULT_TTL = 300
MAX_FLOWS = 16


class IdentitySettings(Protocol):
    tenant: str
    owner: str
    origin: str
    apim: str
    enable_obo: bool
    console_client_id: str
    console_client_secret: str
    obo_client_id: str
    obo_client_secret: str
    gateway_client_id: str


class IdentityError(Exception):
    def __init__(self, detail: str, status: int = 400):
        super().__init__(detail)
        self.status = status


def token_identity(token: str) -> dict[str, Any]:
    # Display metadata only; APIM must still validate the acquired access token.
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError
        claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        if not isinstance(claims, dict):
            raise ValueError
    except (ValueError, binascii.Error):
        raise IdentityError("The acquired token did not contain readable identity metadata.", 502) from None
    text = lambda key: claims.get(key, "") if isinstance(claims.get(key, ""), str) else ""
    scopes = text("scp").split()
    roles = claims.get("roles", [])
    return {
        "kind": "delegated_user" if scopes else "application",
        "principal_object_id": text("oid"),
        "calling_application_id": text("azp") or text("appid"),
        "tenant_id": text("tid"),
        "audience": text("aud"),
        "delegated_scopes": scopes,
        "application_roles": roles if isinstance(roles, list) and all(isinstance(role, str) for role in roles) else [],
        "user_object_id": text("oid") if scopes else None,
        "user_name": text("name") if scopes else None,
        "user_username": (text("preferred_username") or text("upn")) if scopes else None,
    }


@dataclass
class PendingFlow:
    flow: dict[str, Any] | None
    expires_at: float
    result: dict[str, Any] | None = None
    cancelled: bool = False


class UserObo:
    def __init__(
        self,
        settings: IdentitySettings,
        probe: Callable[[str], dict[str, Any]],
        client_factory: Callable[[str, str], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings
        self.probe = probe
        self.client_factory = client_factory or self._client
        self.clock = clock
        self.sessions: dict[str, PendingFlow] = {}
        self.lock = threading.Lock()

    @property
    def unavailable_reason(self) -> str | None:
        if not self.settings.enable_obo:
            return "User OBO is not enabled. Configure ENABLE_DEMO_OBO and the owned Entra applications."
        required = (
            self.settings.tenant, self.settings.owner, self.settings.origin, self.settings.apim,
            self.settings.console_client_id, self.settings.console_client_secret,
            self.settings.obo_client_id, self.settings.obo_client_secret, self.settings.gateway_client_id,
        )
        if not all(required):
            return "User OBO configuration is incomplete; no managed-identity fallback will be used."
        origin = urlsplit(self.settings.origin)
        if origin.scheme != "https" or not origin.hostname or origin.username or origin.query or origin.fragment:
            return "User OBO requires the configured HTTPS console origin."
        try:
            for value in (self.settings.tenant, self.settings.console_client_id, self.settings.obo_client_id, self.settings.gateway_client_id):
                uuid.UUID(value)
        except ValueError:
            return "User OBO application and tenant identifiers must be GUIDs."
        if self.settings.console_client_id == self.settings.obo_client_id:
            return "The interactive sign-in client and console API must be distinct Entra applications."
        return None

    @property
    def console_scope(self) -> str:
        return f"api://{self.settings.console_client_id}/Console.Access"

    @property
    def gateway_scope(self) -> str:
        return f"api://{self.settings.gateway_client_id}/Gateway.Access"

    @property
    def redirect_uri(self) -> str:
        return self.settings.origin + "/api/identity/obo/callback"

    def _client(self, client_id: str, secret: str) -> msal.ConfidentialClientApplication:
        return msal.ConfidentialClientApplication(
            client_id,
            client_credential=secret,
            authority=f"https://login.microsoftonline.com/{self.settings.tenant}",
            exclude_scopes=["offline_access"],
            timeout=20,
        )

    def _cleanup(self) -> None:
        now = self.clock()
        for key in [key for key, session in self.sessions.items() if session.expires_at <= now]:
            del self.sessions[key]

    def start(self) -> tuple[str, str]:
        reason = self.unavailable_reason
        if reason:
            raise IdentityError(reason, 503)
        try:
            client = self.client_factory(self.settings.obo_client_id, self.settings.obo_client_secret)
            flow = client.initiate_auth_code_flow(
                scopes=[self.console_scope], redirect_uri=self.redirect_uri, prompt="select_account", response_mode="form_post",
            )
        except (ValueError, requests.RequestException) as error:
            LOG.warning("identity_signin_start_failed type=%s", type(error).__name__)
            raise IdentityError("Cannot start Entra user sign-in. Check application configuration and connectivity.", 503) from None
        if not isinstance(flow, dict) or not flow.get("state") or not isinstance(flow.get("auth_uri"), str):
            raise IdentityError("Entra sign-in did not return an authorization flow.", 503)
        target = urlsplit(flow["auth_uri"])
        if target.scheme != "https" or target.hostname != "login.microsoftonline.com":
            raise IdentityError("Unexpected authorization endpoint; no redirect was issued.", 503)
        binding = secrets.token_urlsafe(32)
        with self.lock:
            self._cleanup()
            if len(self.sessions) >= MAX_FLOWS:
                raise IdentityError("Too many pending sign-ins. Wait for them to expire before trying again.", 429)
            self.sessions[binding] = PendingFlow(flow=flow, expires_at=self.clock() + FLOW_TTL)
        return binding, flow["auth_uri"]

    @staticmethod
    def _access_token(result: Any, stage: str) -> str:
        if isinstance(result, dict) and isinstance(result.get("access_token"), str) and result["access_token"]:
            return result["access_token"]
        raw_code = result.get("error", "invalid_response") if isinstance(result, dict) else "invalid_response"
        code = raw_code if isinstance(raw_code, str) and re.fullmatch(r"[a-z_]{1,60}", raw_code) else "invalid_response"
        numbers = result.get("error_codes", []) if isinstance(result, dict) else []
        numeric_codes = [str(value) for value in numbers if isinstance(value, int)] if isinstance(numbers, list) else []
        suffix = f" (AADSTS {', '.join(numeric_codes)})" if numeric_codes else ""
        LOG.warning("identity_token_failed stage=%s code=%s", stage, code)
        raise IdentityError(f"Entra {stage} failed: {code}{suffix}. Check the requested scopes and user/admin consent.", 401)

    def complete(self, binding: str, response: Mapping[str, str]) -> None:
        with self.lock:
            self._cleanup()
            session = self.sessions.get(binding)
            if session is None:
                raise IdentityError("The OBO sign-in session expired. Start a new sign-in.", 401)
            if session.flow is None:
                raise IdentityError("This sign-in response was already consumed.", 409)
            if not secrets.compare_digest(str(response.get("state", "")), str(session.flow["state"])):
                raise IdentityError("The sign-in state does not match this browser session.", 401)
            flow = session.flow
            session.flow = None

        try:
            frontend = self.client_factory(self.settings.obo_client_id, self.settings.obo_client_secret)
            authorization = frontend.acquire_token_by_auth_code_flow(flow, dict(response), scopes=[self.console_scope])
            assertion = self._access_token(authorization, "user sign-in")
            claims = authorization.get("id_token_claims")
            oid, tenant = (claims.get("oid"), claims.get("tid")) if isinstance(claims, dict) else (None, None)
            if not isinstance(oid, str) or not isinstance(tenant, str) or oid.casefold() != self.settings.owner.casefold() or tenant.casefold() != self.settings.tenant.casefold():
                raise IdentityError("Sign in as the allowed deployer in the configured tenant. No APIM call was made.", 403)
            self._require_active(binding, session)
            middle_tier = self.client_factory(self.settings.console_client_id, self.settings.console_client_secret)
            exchanged = middle_tier.acquire_token_on_behalf_of(user_assertion=assertion, scopes=[self.gateway_scope])
            token = self._access_token(exchanged, "OBO exchange")
            self._require_active(binding, session)
            result = self.probe(token)
        except IdentityError as error:
            result = {"status": "failed", "action": "identity", "identity_mode": "user_obo", "detail": str(error)}
        except (ValueError, requests.RequestException) as error:
            LOG.warning("identity_flow_failed type=%s", type(error).__name__)
            result = {"status": "failed", "action": "identity", "identity_mode": "user_obo", "detail": "The user sign-in or OBO exchange could not complete. No application-identity fallback was used."}
        with self.lock:
            session.result = result
            session.expires_at = self.clock() + RESULT_TTL

    def _require_active(self, binding: str, session: PendingFlow) -> None:
        with self.lock:
            if session.cancelled or self.sessions.get(binding) is not session:
                raise IdentityError("This user sign-in was cancelled. No APIM call was started.", 409)

    def cancel(self, binding: str) -> None:
        with self.lock:
            session = self.sessions.pop(binding, None)
            if session:
                session.cancelled = True

    def take_result(self, binding: str) -> dict[str, Any]:
        with self.lock:
            self._cleanup()
            session = self.sessions.get(binding)
            if session is None:
                raise IdentityError("No current OBO sign-in result. Start a new sign-in.", 401)
            if session.result is None:
                return {"status": "not_run", "action": "identity", "identity_mode": "user_obo", "detail": "Sign-in or the read-only call is still pending."}
            del self.sessions[binding]
            return session.result
