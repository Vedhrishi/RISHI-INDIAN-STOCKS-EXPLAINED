# Security

## Never commit
`.env`, `token.json`, `client_secret.json`, any `*.key`/`*.pem`, session cookies, or screenshots that show tokens.
These are listed in `.gitignore`. If one is ever pushed, **revoke it at the provider first**, then remove it from history.

## Reporting a vulnerability
Open a private security advisory on the repository (Security tab -> "Report a vulnerability"), or contact the owner through the
profile on GitHub. Please do not post exploit details in a public issue.

## Scope notes
- The toolkit only talks to the providers you configure. It has no telemetry.
- Prefer a dedicated Google account/channel and an API key with a spending limit while testing.
