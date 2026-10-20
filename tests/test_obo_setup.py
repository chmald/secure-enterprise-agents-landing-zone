from __future__ import annotations

import copy

import pytest

from conftest import ROOT, load_module


@pytest.fixture
def setup():
    return load_module("obo_setup_test", ROOT / "scripts" / "configure_console_obo.py")


def test_scope_setup_preserves_unrelated_permissions_and_is_idempotent(setup):
    original = {"requestedAccessTokenVersion": 1, "oauth2PermissionScopes": [{"id": "other", "value": "Other", "isEnabled": True}]}
    before = copy.deepcopy(original)
    updated, scope_id = setup.ensure_scope(original, "Console.Access", "Access console")
    assert original == before
    assert updated["oauth2PermissionScopes"][0] == before["oauth2PermissionScopes"][0]
    repeated, second_id = setup.ensure_scope(updated, "Console.Access", "Access console")
    assert repeated == updated and second_id == scope_id
    updated["oauth2PermissionScopes"][1]["isEnabled"] = False
    with pytest.raises(RuntimeError, match="disabled"):
        setup.ensure_scope(updated, "Console.Access", "Access console")


def test_only_specific_scope_is_preauthorized(setup):
    before = {"preAuthorizedApplications": [{"appId": "existing", "delegatedPermissionIds": ["other"]}]}
    updated = setup.preauthorize(before, "console", "gateway-scope")
    assert before["preAuthorizedApplications"] == [{"appId": "existing", "delegatedPermissionIds": ["other"]}]
    assert updated["preAuthorizedApplications"][1] == {"appId": "console", "delegatedPermissionIds": ["gateway-scope"]}
    assert setup.preauthorize(updated, "console", "gateway-scope") == updated


def test_required_resource_access_is_merged_not_replaced(setup):
    original = [{"resourceAppId": "api", "resourceAccess": [{"id": "old", "type": "Role"}]}]
    updated = setup.require_scope(original, "api", "scope")
    assert original[0]["resourceAccess"] == [{"id": "old", "type": "Role"}]
    assert updated[0]["resourceAccess"] == [{"id": "old", "type": "Role"}, {"id": "scope", "type": "Scope"}]
    assert setup.require_scope(updated, "api", "scope") == updated
