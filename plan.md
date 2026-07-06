# Plan: Task Tracker API

Status: Complete (sample application)
Traces to: [./spec.md](./spec.md) (approved 2026-07-03)
Last updated: 2026-07-03

*Milestones are checked off because this sample was actually implemented,
its tests pass, and its endpoints were manually verified against a real
Postgres instance — see `./README.md` to reproduce.*

## Sequencing principle

Dependency order, bottom-up through the layers of
`../engineering-playbook/core/project-structure.md`: scaffold + config + db
→ model + repository → service + schemas → routers + error handling → tests.
Each milestone leaves the tree importable and the previous layer testable in
isolation.

## Milestone 1 — Scaffold, config, db session ✅

Deliverables:
- Directory tree per `../engineering-playbook/frameworks/fastapi/project-scaffold.md`.
- `app/core/config.py` — `pydantic-settings` `Settings` (Postgres/psycopg
  `DATABASE_URL` default) + cached `get_settings()`.
- `app/core/logging.py` — structured logging + `request_id` context var.
- `app/db/session.py` — engine, `SessionLocal`, `Base`.
- `pyproject.toml` (runtime deps incl. `psycopg[binary]`, dev group),
  `.env.example`, `docker-compose.yml` for local Postgres.

Acceptance criteria:
- `python -c "import app.core.config"` succeeds; `Settings()` reads
  `DATABASE_URL`.
- Package imports cleanly, no circular imports.

Depends on: nothing (first slice)

## Milestone 2 — Model + repository ✅

Deliverables:
- `app/models/task.py` — SQLAlchemy `Task` model with `TaskStatus`/
  `TaskPriority` enums, `id`, `title`, `description`, `status`, `priority`,
  `due_date`, `created_at`, `updated_at`.
- `app/repositories/tasks.py` — `TaskRepository` with `create`/`list`
  (optional status filter)/`get`/`update`/`delete`, the only layer importing
  SQLAlchemy query APIs.

Acceptance criteria:
- Repository tests against a real (test) DB session round-trip a task and
  correctly filter by status.

Depends on: Milestone 1

## Milestone 3 — Service + schemas ✅

Deliverables:
- `app/schemas/task.py` — Pydantic v2 `TaskCreate`, `TaskUpdate` (all fields
  optional, applied via `exclude_unset`), `TaskRead`, `TaskList`.
- `app/schemas/error.py` — the error-envelope response model.
- `app/core/exceptions.py` — `AppError`/`NotFoundError` hierarchy +
  `to_error_response()`.
- `app/services/tasks.py` — `TaskService` orchestrating the repository,
  raising `NotFoundError` for a missing id, applying only explicitly-set
  fields on update.

Acceptance criteria:
- Unit tests: service with a fake repository creates/lists/filters/updates/
  deletes tasks and raises `NotFoundError` on a missing id — no DB, no app.

Depends on: Milestone 2

## Milestone 4 — Routers + error handling + app wiring ✅

Deliverables:
- `app/api/deps.py` — `get_db`, `get_task_service` providers.
- `app/api/v1/routers/tasks.py` — the five endpoints, thin handlers.
- `app/api/v1/routers/health.py` — `/health`, `/ready` (readiness checks DB).
- `app/api/v1/__init__.py` — `/v1` aggregate router.
- `app/main.py` — `create_app()` factory: logging, request-id middleware,
  exception handlers (`AppError` + `RequestValidationError` → envelope),
  router mounting, `init_db()` on startup.

Acceptance criteria:
- App starts against Postgres; `GET /health` returns `200`; all five
  endpoints return the status codes in `spec.md` §4.
- A malformed create body returns `422` in the standard envelope.

Depends on: Milestone 3

## Milestone 5 — Tests + README + manual verification ✅

Deliverables:
- `tests/conftest.py` — in-memory SQLite `db_session` + `client`
  (`TestClient` with `get_db` overridden, `init_db` no-op'd since the test
  schema is created directly on the SQLite engine).
- `tests/unit/` — service unit tests with a fake repository.
- `tests/integration/` — repository tests and `TestClient` tests for all
  five operations, status filtering, and the `404`/`422` envelope.
- `README.md` from `../engineering-playbook/templates/service-readme.md`.
- Manual verification: brought up `docker-compose`'s Postgres, ran the app,
  and drove the full create → list → get → patch → filtered-list → delete
  lifecycle with `curl` against the real database.

Acceptance criteria:
- `pytest` passes (29 tests).
- Manual `curl` walkthrough against real Postgres returns expected status
  codes and bodies, including the error envelope for `404`/`422`.

Depends on: Milestone 4

## Review gates

Because this is a sample application, "review" means the whole thing runs:
`pytest` passes on a clean checkout and the endpoints were manually
exercised against a real Postgres instance (not just SQLite). Each milestone
above was landed so the layer below it was importable and testable before
the next was built.

## Out of scope for this plan

Everything in `spec.md` §3 "Out of scope" (auth, pagination, sub-resources,
search, Alembic migrations, deployment tooling) is deferred and not planned
here — the spec explains why each is left out.
