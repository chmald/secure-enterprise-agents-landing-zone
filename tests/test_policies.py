
import xml.etree.ElementTree as ET
import pytest
from conftest import ROOT

def test_policy_xml_contracts_when_infra_present():
    policy_dir=ROOT/"infra"/"policies"; llm=policy_dir/"llm-api-policy.xml"; mcp=policy_dir/"mcp-api-policy.xml"; fragment=policy_dir/"fragments"/"identity-headers.xml"
    if not llm.exists() or not mcp.exists() or not fragment.exists(): pytest.skip("infra/policies XML files are written by the infra agent")
    llm_text=llm.read_text(); mcp_text=mcp.read_text(); fragment_text=fragment.read_text()
    ET.fromstring(llm_text); ET.fromstring(mcp_text); ET.fromstring(fragment_text)
    required_controls=["validate-azure-ad-token","llm-token-limit","llm-emit-token-metric"]
    missing=[control for control in required_controls if control not in llm_text]
    assert not missing, f"LLM policy missing required controls: {', '.join(missing)}"
    assert 'include-fragment fragment-id="identity-headers"' in mcp_text
    assert "x-gw-" in fragment_text.lower()
    assert "context.Response.Body" not in mcp_text


def test_user_identity_headers_are_validated_not_client_supplied():
    fragment = (ROOT / "infra" / "policies" / "fragments" / "identity-headers.xml").read_text()
    for header in ("x-gw-user-name", "x-gw-user-username", "x-gw-delegated-scopes"):
        assert f'name="{header}" exists-action="delete"' in fragment
        assert f'name="{header}" exists-action="override"' in fragment
    assert "validatedUserOid" in fragment and "preferred_username" in fragment
    for name in ("llm-api-policy.xml", "mcp-api-policy.xml", "records-api-policy.xml"):
        policy = (ROOT / "infra" / "policies" / name).read_text()
        assert "<audience>{{gateway-client-id}}</audience>" in policy
