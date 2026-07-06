# Prompt Library

Reusable Claude Code prompts for common tasks on this project, organized by category. Each prompt file has
three parts:

- **When to use this** — the situation the prompt is for, and when it *isn't* the right tool.
- **Required CLAUDE.md context** — which section(s) of this repo's [`CLAUDE.md`](../CLAUDE.md) the prompt
  assumes are accurate and up to date. If a section has drifted from the real code, fix `CLAUDE.md` first —
  a prompt is only as good as the context it's grounded in.
- **Prompt** — the actual text to paste, with `{{placeholders}}` for the specifics of your situation.

Three prompts were tested end-to-end against this actual codebase (not a copy) before being written up —
each carries a **Tested against** section with the real result. The rest are written to the same standard
but haven't been run here yet; try them, and fold back anything you learn (a wording fix, a missing caveat)
the same way the tested ones were refined.

## Categories

- [`fastapi-endpoints/`](fastapi-endpoints/) — generate an endpoint, add auth, add pagination.
- [`database/`](database/) — optimize a query, design a schema, generate a migration.
- [`testing/`](testing/) — generate a unit test, an integration test, a load test.
- [`debugging/`](debugging/) — explain an error, trace a bug, fix a performance problem.
- [`code-review/`](code-review/) — audit a function, check security, review a PR/diff.
- [`documentation/`](documentation/) — generate API docs, write an ADR, create a runbook.

(A Django/GraphQL category was scoped out — this project is FastAPI-only, so there's nothing real to ground
those prompts against here.)

## Why "Required CLAUDE.md context" is called out separately

A prompt like "add pagination" only produces code that fits this project if Claude already knows this
project's response-wrapper convention, layering, and test setup — that's what `CLAUDE.md` is for. Naming the
exact section per prompt makes two things visible: what has to stay accurate in `CLAUDE.md` for the prompt to
keep working, and what's missing if a prompt produces something that doesn't fit (usually: the relevant
`CLAUDE.md` section was vague, missing, or stale).
