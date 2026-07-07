# Spec: Task Tracker API

Status: Approved
Owner: Engineering (SmartSense) — sample application
Last updated: 2026-07-03

*This spec documents a small, runnable sample service built by applying the
engineering playbook's FastAPI framework layer
(`../engineering-playbook/frameworks/fastapi/`) on top of its
framework-agnostic conventions (`../engineering-playbook/core/`). It follows
the same shape as the playbook's own worked Bookmarks example, swapping
SQLite for Postgres and a `Bookmark` resource for a `Task` resource with an
update path, so the sample also demonstrates a `PATCH` endpoint.*

## 1. Problem Statement

Small teams and individuals tracking day-to-day work items (tasks, todos,
follow-ups) often have no shared, queryable store with a clean API — the
alternative is a spreadsheet, a chat thread, or sticky notes with no
programmatic access. There's no single HTTP surface a script, CLI, or
frontend can call to create a task, list open work, move a task through a
status lifecycle (todo → in progress → done), and remove it once complete.

This is also the smallest realistic shape that exercises a persisted
resource with a genuine state-transition (status), a full CRUD-plus-update
surface, an error contract, config, and logging — backed by Postgres rather
than a toy embedded database — without incidental complexity (no auth
server, no multi-tenancy, no async fan-out) obscuring the pattern.

## 2. Audience

- **Internal tools, scripts, and small frontends** that need to create and
  track tasks over HTTP (the primary consumer).
- **Engineers cloning this as a starting point** for a real task-tracking
  service or for any other single-resource CRUD API on Postgres.

Primary interaction: a JSON HTTP API — create a task, list tasks (optionally
filtered by status), fetch one by id, update its status/fields, delete one.

## 3. Scope

### In scope

- A `Task` resource with fields: `id`, `title`, `description`, `status`
  (`todo` | `in_progress` | `done`), `priority` (`low` | `medium` | `high`),
  `due_date`, `created_at`, `updated_at`.
- Five endpoints under a `/v1` prefix:
  - `POST /v1/tasks` — create a task, returns `201` + the resource.
  - `GET /v1/tasks` — list tasks, newest first, optional `?status=` filter.
  - `GET /v1/tasks/{id}` — fetch one, `404` if it doesn't exist.
  - `PATCH /v1/tasks/{id}` — partially update any of `title`, `description`,
    `status`, `priority`, `due_date`; omitted fields are left unchanged;
    `404` if it doesn't exist.
  - `DELETE /v1/tasks/{id}` — delete one, `204`, `404` if it doesn't exist.
- Postgres persistence via SQLAlchemy (psycopg v3 driver) through a real
  repository layer.
- The layered architecture from `../engineering-playbook/core/project-structure.md`
  (routers → services → repository → models).
- The standard error envelope from `../engineering-playbook/core/api-design.md`
  via a centralized exception handler.
- Structured logging with a request-id per
  `../engineering-playbook/core/logging-observability.md`, plus `/health` and
  `/ready` endpoints (readiness checks the DB).
- Typed config via `pydantic-settings` per
  `../engineering-playbook/core/configuration-secrets.md`.
- `docker-compose.yml` providing a local Postgres instance for development.
- A pytest suite (unit + integration) covering all five operations, status
  filtering, and the `404`/`422` error-envelope paths.

### Out of scope

- Authentication and authorization — no user model; the service is a
  single-tenant store. (Where per-user ownership *would* go is noted in code
  comments pointing at `../engineering-playbook/core/security-basics.md`, but
  isn't built.)
- Pagination — the list endpoint returns all matching rows; fine for a
  sample with a bounded dataset. Cursor pagination
  (`../engineering-playbook/core/api-design.md`) would be the first addition
  if this grew into a real product.
- Sub-resources such as comments, attachments, assignees, projects, or tags.
  **Update:** comments are no longer out of scope — see
  `.claude/specs/task-comments/spec.md` for the approved follow-up spec that
  adds `Task` comments. Attachments, assignees, projects, and tags remain
  out of scope.
- Full-text search or sorting options beyond newest-first.
- Schema migrations tooling (Alembic) — the sample creates tables on startup
  via `Base.metadata.create_all()` for simplicity; a real service would run
  migrations instead (noted in the README).
  **Update:** Alembic was subsequently adopted — see
  `.claude/specs/task-comments-migration/spec.md` for the approved
  follow-up spec.
- Production deployment concerns (containerizing the API itself, a secrets
  manager, CI/CD) — the README covers local run only.

## 4. Success Criteria

- `pytest` passes with tests covering create, list (incl. status filter),
  get, update, delete, and the `404`/`422` error-envelope shapes.
- The five endpoints behave per the status-code table in
  `../engineering-playbook/core/api-design.md` (`201`/`200`/`204`/`404`/`422`).
- No layer violates `../engineering-playbook/core/project-structure.md`:
  routers contain no SQL or business logic, only the repository imports
  SQLAlchemy query APIs.
- Every error response — including FastAPI's own validation `422` — uses the
  `../engineering-playbook/core/api-design.md` envelope, produced by exactly
  one exception handler.
- A reader can bring up Postgres via `docker-compose up`, run the app, and
  run the tests from the README on a clean checkout.
- Manually verified: full create → list → get → patch(status) → filtered
  list → delete lifecycle against a real Postgres instance returns the
  expected status codes and bodies.

## 5. Non-goals

- **Not a feature-complete task-management product** — no projects, no
  assignees, no notifications, no UI. It's an API shape, deliberately
  minimal.
- **Not a demonstration of async FastAPI** — it uses sync SQLAlchemy and
  `def` handlers on purpose
  (`../engineering-playbook/frameworks/fastapi/idioms.md` explains when to
  choose which).
- **Not a benchmark or performance example** — optimizes for readability
  and correctness, not throughput or scale.

## 6. Open Questions

- Should status transitions be constrained (e.g. `done` → `todo` disallowed)
  rather than a free-form enum set? (Owner: sample maintainers — deferred;
  no business rule was requested, and an unconstrained enum keeps the
  example simple. Revisit if this becomes a real product.)
- Should the example add Alembic migrations instead of `create_all()` on
  startup? (Owner: sample maintainers — deferred for the same reason the
  playbook's Bookmarks example defers it; noted in the README as the
  natural next step.)
  **Update:** Resolved — see `.claude/specs/task-comments-migration/spec.md`.

---

## Review gate

Approved for the purpose of this sample application so the plan and
implementation could proceed and be validated end-to-end against a real
Postgres instance.

Approved by: Engineering (SmartSense) — sample application
Date: 2026-07-03
