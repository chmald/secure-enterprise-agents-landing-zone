
import json, pytest
from conftest import ROOT

def test_azd_parameters_are_quoted_when_infra_present():
    params=ROOT/"infra"/"azd.parameters.json"; azd_bicep=ROOT/"infra"/"azd.bicep"
    if not params.exists() or not azd_bicep.exists(): pytest.skip("infra azd files are written by the infra agent")
    data=json.loads(params.read_text())
    for name,value in data.get("parameters",{}).items(): assert isinstance(value.get("value"), str), f"{name} value must be a quoted azd substitution"
    assert "targetScope = 'subscription'" in azd_bicep.read_text()


def _modules():
    return ROOT/"infra"/"modules"


def test_console_easy_auth_explicitly_allows_only_its_own_browser_origin():
    text = (_modules() / "demo-console.bicep").read_text()
    assert "login: {\n      allowedExternalRedirectUrls: [\n        consoleUrl\n      ]\n    }" in text
    assert "var consoleUrl = 'https://${appName}.${defaultDomain}'" in text
    assert "requireHttps: true" in text
    assert "allowedPrincipals:" in text and "allowedUserId" in text


def test_isolation_creates_private_endpoints_and_dns_zones():
    main=ROOT/"infra"/"main.bicep"; dns=_modules()/"private-dns.bicep"
    if not main.exists() or not dns.exists(): pytest.skip("isolation modules not present")
    text=main.read_text(); zones=dns.read_text()
    for zone in ["privatelink.cognitiveservices.azure.com","privatelink.openai.azure.com","privatelink.services.ai.azure.com","privatelink.vaultcore.azure.net","privatelink.azurecr.io","privatelink.azure-api.net","privatelink.documents.azure.com","privatelink.search.windows.net"]:
        assert zone in zones, zone
    assert "privatelink.blob." in zones
    for group in ["groupId: 'account'","groupId: 'vault'","groupId: 'registry'","groupId: 'Gateway'"]:
        assert group in text, group
    assert "agentSubnetId: networkIsolation" in text


def test_isolation_binds_agent_subnet_and_disables_public_access():
    foundry=(_modules()/"foundry.bicep").read_text()
    assert "networkInjections" in foundry and "scenario: 'agent'" in foundry
    assert "networkIsolation ? 'Premium' : 'Standard'" in foundry
    assert "networkIsolation ? 'Disabled' : 'Enabled'" in (_modules()/"keyvault.bicep").read_text()
    assert "Microsoft.App/environments" in (_modules()/"network.bicep").read_text()
    assert "Microsoft.Web/serverFarms" in (_modules()/"network.bicep").read_text()
