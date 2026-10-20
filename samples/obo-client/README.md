# User sign-in → Foundry sample (legacy `obo-client` path)

This sample signs in a user with an explicit tenant and invokes the Foundry project hosted-agent Responses endpoint. It prints the response and a trace ID. **It does not implement an on-behalf-of (OBO) downstream token exchange.** A signed-in caller reaching Foundry does not make the hosted agent delegate that user's identity to APIM or tools; the shipped agents still use their app-only instance identities.

The folder name and `invoke_as_user.py` entry point remain for backward compatibility. Supply a deployed `--endpoint`, `--tenant-id`, `--client-id`, and the scope/audience accepted by that Foundry endpoint. Argument parsing, sign-in/token wiring, trace generation and request shape are separate checks from downstream identity/audit verification; no live OBO proof is supplied by this sample.

For the implemented **console-to-APIM user OBO** comparison, use [console setup](../../docs/03-deployment.md#optional-console-to-apim-user-obo) and the [three-app identity flow](../../docs/07-identity-auth-traceability.md#console-to-apim-user-obo-three-apps). It is disabled by default and performs only catalog MCP discovery, not hosted-agent delegation or user/record-level business authorization. Require actual human sign-in and the probe's trace-matched audit rows before claiming success; keep real operator identity metadata private.

*Last updated: 2026-10-20*
