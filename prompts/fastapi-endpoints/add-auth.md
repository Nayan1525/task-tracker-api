# Add Authentication to FastAPI Endpoints

## When to use this

This service currently has **no authentication at all** on `/v1/*` — a deliberate, documented scope decision
for the sample (see `spec.md`), not an oversight (see `CLAUDE.md`'s Security section). Use this prompt when
that decision changes and auth becomes real, new scope — not to patch a perceived gap without confirming the
decision has actually changed.

## Required CLAUDE.md context

The **Dependency Injection** and **Security** sections of [`CLAUDE.md`](../../CLAUDE.md) — auth belongs in a
`Depends()`, never a global, and secrets must come from the typed `Settings` object, never hardcoded.

## Prompt

```
I need to add authentication to this FastAPI service. This is a deliberate scope change from the documented
"no auth" state in spec.md — confirm you understand that before proceeding, don't treat it as fixing a bug.

Scheme: {{"API key in a header", "JWT bearer token", "OAuth2 via an existing identity provider" — or "not
decided yet, recommend one for a {{internal service / public API / etc.}}"}}
Scope: {{which endpoints/routers need it — e.g. "all of /v1/*, leave /health and /ready open"}}
Credential source: {{where the valid credential/secret/key comes from — env var, a table, an external IdP}}

Please:
1. Implement the check as a Depends()-based dependency in app/core/ (follow this project's existing
   core/api/deps.py layout, don't invent a new location).
2. Never hardcode the secret/key — read it via app/core/config.py's Settings object, adding a new field there.
3. Return the project's existing error envelope (see app/core/exceptions.py's AppError/to_error_response) on
   missing/invalid credentials — not FastAPI's bare default 401/403.
4. Apply the dependency at the router level matching the scope above (app/api/v1/__init__.py's aggregate
   router, most likely) — don't wrap it around /health or /ready.
5. Add tests: a request with no credential, an invalid one, and a valid one, for at least one protected
   endpoint — reuse the existing `client` fixture from tests/conftest.py, and check whether the shared fixture
   needs a default valid credential so the other 29+ existing tests don't all start failing once this lands.
6. Document the new required header/credential in .env.example, matching how DATABASE_URL etc. are documented
   there.

If the scheme requires a new dependency (e.g. a JWT library), name it and ask before adding it.
```

## Tested against

Not executed against this project in this pass. When you do run it: pay close attention to step 5's fixture
concern — this is the single biggest way this prompt goes wrong. This project's `client` fixture in
`tests/conftest.py` is shared by every existing integration test; if auth is applied to all of `/v1/*`
without also updating that fixture to authenticate by default, the entire integration suite starts failing at
once, not just the tests that should exercise the new auth behavior. Confirm the full suite still passes after
applying this prompt, not just the new auth-specific tests.
