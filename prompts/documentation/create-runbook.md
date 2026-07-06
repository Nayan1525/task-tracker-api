# Create an Operational Runbook

## When to use this

Once this service is (or is about to be) running somewhere someone would be paged for, and there's no written
procedure for its known failure modes. Not needed while it's purely a local sample nobody's on call for.

## Required CLAUDE.md context

The **Commands** and **Environment & Secrets** sections of [`CLAUDE.md`](../../CLAUDE.md), plus **Migrations**
(rollback interacts directly with whether Alembic exists yet).

## Prompt

```
Create an operational runbook for the Task Tracker API.

Known failure modes so far: {{list any, or "none yet — infer likely ones from the code/architecture"}}
On-call audience: {{"engineers familiar with this service", "a shared rotation with less context"}}

Please:
1. Start with the essentials for the first 60 seconds: what this service does, its one dependency (Postgres),
   where logs are (structured JSON with X-Request-ID, per app/core/logging.py and the request-id middleware in
   app/main.py), and how to use /health vs /ready to tell if this service is actually the source of an alert.
2. For each known/likely failure mode inferred from the real code (DB unreachable — see /ready's check in
   app/api/v1/routers/health.py; a bad deploy; request validation errors spiking): symptoms, likely cause,
   diagnostic steps using this project's actual tooling (docker compose ps postgres, the real DATABASE_URL
   shape from .env.example), and mitigation steps in order.
3. Cover rollback, and be explicit about how this project's current create_all()-at-startup approach (see
   CLAUDE.md's Migrations section) affects it — create_all() cannot undo a column add/drop, so "roll back the
   deploy" does not mean "roll back the schema" unless Alembic has since been introduced.
4. Call out anything genuinely dangerous (a destructive command, an irreversible schema change) with an
   explicit warning.
5. Keep it specific to this codebase — no generic "check if the server is up" filler.
```

## Tested against

Not executed against this project in this pass. Step 3 is the detail most likely to get glossed over if you
skip live-testing this one: because there's no Alembic yet, "rollback" for a schema-affecting deploy on this
project today genuinely has no clean undo path — a runbook that doesn't say that plainly is worse than no
runbook, since it implies a safety net that doesn't exist.
