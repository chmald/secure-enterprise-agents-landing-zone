function Initialize-DemoConsoleAuth {
    param([Parameter(Mandatory = $true)][string]$EnvironmentName)

    $userId = (& az ad signed-in-user show --query id -o tsv).Trim()
    if ($LASTEXITCODE -ne 0 -or $userId -notmatch '^[0-9a-fA-F-]{36}$') {
        throw "The demo console requires an interactive human deployer in the target tenant. Sign in with az login --tenant <demo-tenant>."
    }
    $allowedId = Get-EnvValue -Name "DEMO_CONSOLE_ALLOWED_USER_ID"
    if ($allowedId -and $allowedId -ne $userId) {
        throw "The signed-in deployer differs from DEMO_CONSOLE_ALLOWED_USER_ID. Refusing to transfer console access implicitly."
    }
    Set-AzdEnvironmentValue -Name "DEMO_CONSOLE_ALLOWED_USER_ID" -Value $userId

    $clientId = Get-EnvValue -Name "DEMO_CONSOLE_CLIENT_ID"
    if (-not $clientId) {
        $appJson = & az ad app create --display-name "console-$EnvironmentName" --sign-in-audience AzureADMyOrg --enable-id-token-issuance true -o json
        if ($LASTEXITCODE -ne 0) { throw "Cannot create the console Entra app. Application registration permission is required." }
        $clientId = [string](($appJson | ConvertFrom-Json).appId)
        Set-AzdEnvironmentValue -Name "DEMO_CONSOLE_CLIENT_ID" -Value $clientId
    }
    $audience = & az ad app show --id $clientId --query signInAudience -o tsv
    if ($LASTEXITCODE -ne 0 -or "$audience".Trim() -ne "AzureADMyOrg") {
        throw "The console Entra application must exist in the target tenant and be single-tenant (AzureADMyOrg)."
    }
    # Parenthesized JMESPath expressions are reinterpreted by the Windows az.cmd wrapper.
    $servicePrincipalId = & az ad sp list --filter "appId eq '$clientId'" --query "[0].id" -o tsv
    if ($LASTEXITCODE -ne 0) { throw "Cannot check the console enterprise application." }
    if ([string]::IsNullOrWhiteSpace([string]$servicePrincipalId)) {
        & az ad sp create --id $clientId -o none
        if ($LASTEXITCODE -ne 0) { throw "Cannot create the console enterprise application." }
    }
    if (-not (Get-EnvValue -Name "DEMO_CONSOLE_CLIENT_SECRET")) {
        $credentialJson = & az ad app credential reset --id $clientId --append --display-name "demo-console" --years 1 -o json
        if ($LASTEXITCODE -ne 0) { throw "Cannot create the console sign-in credential." }
        $secret = [string](($credentialJson | ConvertFrom-Json).password)
        if (-not $secret) { throw "The console sign-in credential was empty." }
        # azd env set normally prints a confirmation only; suppress all output for secret material.
        & azd env set DEMO_CONSOLE_CLIENT_SECRET $secret | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Cannot save the console credential to the local azd environment." }
        [Environment]::SetEnvironmentVariable("DEMO_CONSOLE_CLIENT_SECRET", $secret, "Process")
        Write-Host "Created the console sign-in credential (expires in one year). Kept in the local azd environment and the Container App secret, never in browser configuration."
    }
}

function Set-DemoConsoleRedirectUri {
    $url = Get-EnvValue -Name "DEMO_CONSOLE_URL"
    $clientId = Get-EnvValue -Name "DEMO_CONSOLE_CLIENT_ID"
    if (-not $url -or -not $clientId) { throw "Console URL and client ID are required to configure the sign-in callback." }
    & az ad app update --id $clientId --web-redirect-uris "$($url.TrimEnd('/'))/.auth/login/aad/callback" --enable-id-token-issuance true | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to configure the console Entra callback URL." }
    Write-Host "Demo console: $url (Entra sign-in, deploying user only)."
}
