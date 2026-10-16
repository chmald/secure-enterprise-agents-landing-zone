from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import ROOT


@pytest.mark.parametrize("scenario", ["create", "reuse", "wrong-owner", "wrong-audience", "redirect"])
def test_console_auth_hooks_with_mocked_clis(scenario):
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell is required for hook execution tests.")
    script = r"""
$ErrorActionPreference = "Stop"
. '__COMMON__'
. '__AUTH__'
$global:LASTEXITCODE = 0
$script:calls = [System.Collections.Generic.List[string]]::new()
$env:DEMO_CONSOLE_ALLOWED_USER_ID = ""
$env:DEMO_CONSOLE_CLIENT_ID = ""
$env:DEMO_CONSOLE_CLIENT_SECRET = ""
$env:DEMO_CONSOLE_URL = "https://console.example"
$scenario = '__SCENARIO__'
if ($scenario -in @("reuse", "wrong-audience")) {
    $env:DEMO_CONSOLE_CLIENT_ID = "app-client"
    $env:DEMO_CONSOLE_CLIENT_SECRET = "existing-secret"
}
if ($scenario -eq "wrong-owner") { $env:DEMO_CONSOLE_ALLOWED_USER_ID = "different-owner" }
function az {
    $command = $args -join " "
    $script:calls.Add($command)
    $global:LASTEXITCODE = 0
    switch -Wildcard ($command) {
        "ad signed-in-user show*" { return "11111111-1111-1111-1111-111111111111" }
        "ad app create*" { return '{"appId":"app-client"}' }
        "ad app show*" { if ($scenario -eq "wrong-audience") { return "AzureADMultipleOrgs" }; return "AzureADMyOrg" }
        "ad sp list*" { if ($scenario -eq "reuse") { return "existing-principal" }; return }
        "ad sp create*" { return }
        "ad app credential reset*" { return '{"password":"new-secret"}' }
        "ad app update*" { return }
        default { throw "Unexpected az command: $command" }
    }
}
function azd {
    $global:LASTEXITCODE = 0
    if (($args -join " ") -notlike "env set *") { throw "Unexpected azd command" }
}
$threw = $false
try {
    if ($scenario -eq "redirect") {
        $env:DEMO_CONSOLE_CLIENT_ID = "app-client"
        Set-DemoConsoleRedirectUri
    } else {
        Initialize-DemoConsoleAuth -EnvironmentName "test"
    }
} catch {
    $threw = $true
    if ($scenario -notin @("wrong-owner", "wrong-audience")) { throw }
}
if ($scenario -in @("wrong-owner", "wrong-audience") -and -not $threw) { throw "Expected refusal" }
if ($scenario -eq "wrong-owner" -and $script:calls.Count -ne 1) { throw "Must stop before changing app configuration" }
if ($scenario -eq "create" -and $env:DEMO_CONSOLE_CLIENT_SECRET -ne "new-secret") { throw "Credential was not persisted" }
if ($scenario -eq "create" -and ($script:calls -like "ad app create*") -notlike "*--enable-id-token-issuance true*") { throw "New console app must issue ID tokens for the Easy Auth hybrid flow" }
if ($scenario -eq "reuse" -and ($script:calls -like "*credential reset*")) { throw "Existing credential must not be reset" }
if ($scenario -eq "reuse" -and ($script:calls -like "ad sp create*")) { throw "Existing enterprise application must not be recreated" }
if ($scenario -eq "redirect" -and ($script:calls -join " ") -notlike "*/.auth/login/aad/callback*") { throw "Wrong callback URI" }
if ($scenario -eq "redirect" -and ($script:calls -join " ") -notlike "*--enable-id-token-issuance true*") { throw "Existing console app must issue ID tokens for the Easy Auth hybrid flow" }
"""
    script = script.replace("__COMMON__", str(ROOT / "infra/hooks/common.ps1")).replace("__AUTH__", str(ROOT / "infra/hooks/console-auth.ps1")).replace("__SCENARIO__", scenario)
    result = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "new-secret" not in result.stdout


@pytest.mark.parametrize("scenario", ["missing", "existing", "lookup-failed"])
@pytest.mark.skipif(os.name != "nt", reason="Exercises the Windows az.cmd argument parser.")
def test_console_enterprise_lookup_through_windows_cmd_wrapper(tmp_path, scenario):
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell is required for hook execution tests.")
    (tmp_path / "az.cmd").write_text(
        '@IF EXIST "%~dp0shim.py" (\n'
        '  "%DEMO_TEST_PYTHON%" "%~dp0shim.py" %*\n'
        ') ELSE (\n'
        '  exit /b 1\n'
        ')\n', encoding="utf-8",
    )
    (tmp_path / "shim.py").write_text(
        """import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["DEMO_TEST_CALLS"]).open("a", encoding="utf-8") as calls:
    calls.write(json.dumps(args) + "\\n")
if args[:3] == ["ad", "signed-in-user", "show"]:
    print("11111111-1111-1111-1111-111111111111")
elif args[:3] == ["ad", "app", "show"]:
    print("AzureADMyOrg")
elif args[:3] == ["ad", "sp", "list"]:
    if os.environ["DEMO_TEST_SCENARIO"] == "lookup-failed":
        sys.exit(1)
    if os.environ["DEMO_TEST_SCENARIO"] == "existing":
        print("existing-principal")
elif args[:3] != ["ad", "sp", "create"]:
    sys.exit(2)
""", encoding="utf-8",
    )
    calls_path = tmp_path / "calls.jsonl"
    env = {
        **os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
        "DEMO_TEST_PYTHON": sys.executable, "DEMO_TEST_CALLS": str(calls_path),
        "DEMO_TEST_SCENARIO": scenario,
        "DEMO_CONSOLE_ALLOWED_USER_ID": "", "DEMO_CONSOLE_CLIENT_ID": "app-client",
        "DEMO_CONSOLE_CLIENT_SECRET": "existing-secret",
    }
    script = (
        f". '{ROOT / 'infra/hooks/common.ps1'}'; "
        f". '{ROOT / 'infra/hooks/console-auth.ps1'}'; "
        'function azd { $global:LASTEXITCODE = 0 }; '
        'Initialize-DemoConsoleAuth -EnvironmentName test'
    )
    result = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", script], env=env, capture_output=True, text=True)
    assert "-o was unexpected" not in result.stdout + result.stderr
    calls = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()]
    if scenario == "lookup-failed":
        assert result.returncode != 0
        assert "Cannot check the console enterprise application" in result.stderr
    else:
        assert result.returncode == 0, result.stdout + result.stderr
    creates = [args for args in calls if args[:3] == ["ad", "sp", "create"]]
    assert len(creates) == (1 if scenario == "missing" else 0)
