# Generate API Documentation

## When to use this

This service's endpoints have drifted from (or never had) written documentation beyond `/docs`'s
auto-generated OpenAPI view — producing a human-readable reference grounded in what the API actually does, not
what `README.md`'s curl examples say it does.

## Required CLAUDE.md context

The **Routers** and **Pydantic Models** sections of [`CLAUDE.md`](../../CLAUDE.md) — to describe request/
response shapes and error behavior accurately.

## Prompt

```
Generate API documentation for the /v1/tasks and /health, /ready endpoints.

Audience: {{"other engineers on this team", "external consumers"}}
Format: {{"a standalone API.md", "Markdown to add to README.md"}}

Please:
1. Derive the documentation from the actual current code (app/api/v1/routers/, app/schemas/task.py) — not from
   README.md's curl examples, which may have drifted. Flag any place where an existing example in README.md
   appears wrong, incomplete, or inconsistent with the real behavior.
2. For each endpoint: method, path, purpose, request shape (required/optional fields + types, from
   TaskCreate/TaskUpdate), response shape for success (from TaskRead/TaskList), and the specific error
   responses it can actually return (status code + when — from app/core/exceptions.py's exception hierarchy).
3. Include one realistic example request/response per endpoint with real values, not `{{}}` placeholders.
4. Note authentication requirements per endpoint — this API currently has none; say so plainly rather than
   omitting the topic.
5. If you find an endpoint whose actual behavior doesn't match an apparent design intent, flag it as a
   discrepancy for me to confirm.
```

## Tested against

Not executed against this project in this pass. One known real discrepancy worth confirming if you do run
this: `README.md`'s curl walkthrough runs `GET /v1/tasks?status=in_progress` *before* the `PATCH` that actually
sets a task to `in_progress` — followed in that literal order it returns an empty `{"data": []}`, which reads
as broken unless you notice the walkthrough is illustrative, not meant to be run as a strict sequence.
