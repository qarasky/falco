# Errors for AI agents

Falco's own errors are one JSON object per line on stderr:

```json
{"error":"CONNECTION_TIMEOUT","message":"Timed out connecting to the configured SSH server.","action":"Check the host/IP, SSH port, server availability and required VPN.","target":"deploy@100.64.0.12:22"}
```

Codes distinguish network, authentication, credential-store, host-key and remote
operation failures, with a suggested next action. A timeout does not mean the
password is wrong. Check any required VPN, and inspect partial effects before
retrying commands or transfers. Falco never automatically retries a command.

If `CREDENTIAL_SETUP_REQUIRED` appears, ask the user to complete terminal
setup—never request their password or private-key passphrase in chat, pass it
through argv/environment, or capture the hidden prompt.

If `HOST_KEY_CHANGED` appears, ask the user to verify the new fingerprint and
authorize the change before using `--accept-new-key`.

Launcher error exit groups are `2` (arguments/config), `3` (local credentials),
and `4` (SSH/remote operations). Remote commands return their own exit codes, so
use a Falco JSON diagnostic to distinguish a launcher failure from remote stderr.
Remote stderr is streamed unchanged and may not be JSON.

[Back to the README](../README.md)
