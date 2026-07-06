# Check Security of a Change or Component

## When to use this

Before shipping anything that touches authentication/authorization, handles untrusted input, or adds a new
externally-reachable surface — a focused security pass, not a general code review (pair with `review-pr.md`
for the rest).

## Required CLAUDE.md context

The **Security** and **Environment & Secrets** sections of [`CLAUDE.md`](../../CLAUDE.md) — in particular, that
this service has *no authentication by design* right now, which changes what counts as a real finding versus
an expected, already-documented state.

## Prompt

```
Do a security review of {{the function/endpoint/file — be specific}}.

What it does: {{brief description}}
Trust boundary: {{who/what can reach this}}

Please check specifically, citing line numbers:
1. Input validation — is every external input validated through app/schemas/, not hand-parsed?
2. Injection — any raw SQL string interpolation, or unescaped input reaching a query? (This project uses the
   SQLAlchemy ORM throughout — flag it clearly if you find an exception to that.)
3. AuthN/AuthZ — does this check who the caller is and what they're allowed to do? If the answer is "there's no
   auth at all," confirm against CLAUDE.md's Security section whether that's the documented, deliberate state
   before flagging it as a discovered vulnerability rather than a known, scoped decision.
4. Secrets — anything hardcoded, logged, or returned in a response body that shouldn't be? Check
   app/core/config.py's default DATABASE_URL specifically — is a hardcoded default credential there actually a
   finding, or an intentional dev-only default that's always overridden in real environments?
5. Error responses — does a 5xx ever leak internal detail (stack trace, raw exception message) to the client?
   Check against app/core/exceptions.py's to_error_response.

Classify each finding by real-world impact, and explicitly rule out anything that isn't actually exploitable
given the stated trust boundary rather than padding the list.
```

## Tested against

**Ran directly against this repo** (read-only — `app/main.py`, `app/core/config.py`, `app/core/exceptions.py`,
`app/api/v1/routers/tasks.py`, `app/api/v1/routers/health.py`). Findings:
- **No auth on `/v1/*`** — confirmed against `spec.md`/`CLAUDE.md` as a documented, deliberate scope decision,
  not a discovered bug. Correctly classified as *acknowledged, not a finding*, per the prompt's own step-3
  instruction — this is exactly the case that instruction exists for.
- **Input validation**: clean. Every request body goes through `TaskCreate`/`TaskUpdate`; the one query param
  (`status`) is typed `TaskStatus | None` via FastAPI's `Query()`, rejected with 422 if invalid.
- **Injection**: clean. `TaskRepository.list()` uses `select(Task).where(Task.status == status)` — parameterized
  via the ORM, no string interpolation anywhere in the repository layer. `health.py`'s one raw `text("SELECT 1")`
  has no user input in it.
- **Secrets**: `app/core/config.py`'s default `database_url` has a hardcoded `task_tracker:task_tracker`
  credential — ruled out as a real finding (Informational only) since it matches `docker-compose.yml`'s local
  dev default and is always overridden via `DATABASE_URL` in any real environment; the prompt's step-4
  instruction to check whether this is "an intentional dev-only default" is what correctly prevented over-flagging it.
- **Error responses**: clean. `to_error_response` returns a generic `"An unexpected error occurred."` for any
  5xx and only logs the real exception server-side (`app/core/exceptions.py:49-53`) — no internal leak to the
  client confirmed by reading the actual mapping logic, not assumed.

No wording changes needed — the prompt's explicit "confirm against CLAUDE.md before flagging" instructions did
their job: the review produced zero real findings on an app with no auth, which is the *correct* result given
the documented scope, not a sign the review was too shallow.
