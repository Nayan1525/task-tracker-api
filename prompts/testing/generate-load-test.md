# Generate a Load Test

## When to use this

Before a launch, after a change likely to affect capacity (a new query, an endpoint expected to see real
traffic), or when investigating a suspected throughput/latency ceiling — to get real numbers instead of
guessing.

## Required CLAUDE.md context

The **Commands** section of [`CLAUDE.md`](../../CLAUDE.md) (how to run this service locally) and
**Environment & Secrets** (so the load test targets a safe, non-production instance).

## Prompt

```
Write a load test for {{endpoint(s), e.g. "GET /v1/tasks and POST /v1/tasks"}}.

Target: local dev server ({{never point this at a shared/production instance without saying so explicitly}})
Load profile: {{e.g. "20 concurrent users, ramp over 10s, hold 20s" — give the rate math explicitly: spawn
rate = users ÷ ramp-seconds, total run time = ramp + hold, so it translates cleanly to whatever tool is used}}
Success criteria: {{e.g. "p95 latency under 500ms, 0% error rate" or ask me for realistic numbers}}

Please:
1. Use a real load-testing tool (Locust is a reasonable default if nothing else is set up) — name any new
   dependency before adding it.
2. Script realistic requests: for POST /v1/tasks, a valid payload matching TaskCreate's fields
   (app/schemas/task.py), not an empty body.
3. Make the target host configurable (CLI flag/env var), defaulting to localhost — never hardcode a
   non-local URL.
4. Run it against a locally running instance of this app (uvicorn app.main:app, pointed at a throwaway
   SQLite/Postgres DB) and report the actual results — throughput, latency percentiles, error rate — against
   the success criteria above.
```

## Tested against

Not executed against this project in this pass. Worth knowing before running it here: this app's default
`DATABASE_URL` points at Postgres on `localhost:5433` (`docker-compose.yml`) — either bring that container up
first or override `DATABASE_URL` to a local SQLite file for the load-test run, and say explicitly which one
you did, since the two have very different real-world performance characteristics.
