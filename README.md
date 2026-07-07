# Task Tracker API

A small, runnable FastAPI + Postgres service — CRUD (plus status updates) for
a `Task` resource. Built by applying the engineering playbook's FastAPI
framework layer (`../engineering-playbook/frameworks/fastapi/`) on top of its
framework-agnostic conventions (`../engineering-playbook/core/`), following
the `spec → plan → implement` workflow (see `spec.md` and `plan.md`).

## Status

Owner: Engineering (SmartSense) — sample application
On-call: n/a (sample service, not deployed)
Spec: [`./spec.md`](./spec.md)
Plan: [`./plan.md`](./plan.md)

## Architecture at a glance

Layered per `../engineering-playbook/core/project-structure.md`, implemented
per `../engineering-playbook/frameworks/fastapi/project-scaffold.md`:

```
HTTP → app/api/v1/routers/  (thin handlers)
       → app/services/       (business logic, raises domain errors)
         → app/repositories/ (the only layer touching the DB)
           → app/models/     (SQLAlchemy ORM) → Postgres
```

- Request/response bodies are Pydantic v2 schemas (`app/schemas/`), never the
  ORM model directly.
- Errors use the one envelope from `../engineering-playbook/core/api-design.md`,
  produced by a single exception handler in `app/main.py`.
- Structured JSON logging with a per-request `X-Request-ID`; `/health` and
  `/ready` are distinct (`/ready` checks the DB).
- Config is a typed `pydantic-settings` object (`app/core/config.py`).

## Running locally

From a clean checkout, in this directory:

```bash
# 1. create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. install the app + dev dependencies
pip install -e .
pip install pytest httpx           # dev group (see pyproject.toml)

# 3. start Postgres (host port 5433, to avoid clashing with a local
#    system Postgres on 5432 — see docker-compose.yml)
docker compose up -d postgres

# 4. configure environment
cp .env.example .env               # defaults already match docker-compose.yml

# 5. apply migrations (schema is Alembic-managed — see "Migrations" below)
alembic upgrade head

# 6. run the service
uvicorn app.main:app --reload
```

Service runs at: http://localhost:8000
Interactive API docs (OpenAPI/Swagger): http://localhost:8000/docs

Try it:

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title": "Write onboarding doc", "description": "For new hires", "priority": "high", "due_date": "2026-08-01"}'

curl http://localhost:8000/v1/tasks
curl http://localhost:8000/v1/tasks/1
curl "http://localhost:8000/v1/tasks?status=in_progress"
curl -X PATCH http://localhost:8000/v1/tasks/1 -H 'Content-Type: application/json' -d '{"status": "in_progress"}'

curl -X POST http://localhost:8000/v1/tasks/1/comments \
  -H 'Content-Type: application/json' \
  -d '{"author": "Alice", "message": "Blocked on design review"}'
curl http://localhost:8000/v1/tasks/1/comments

curl -X DELETE http://localhost:8000/v1/tasks/1
curl http://localhost:8000/v1/tasks/999   # 404 error envelope
```

## Task fields

`Task` (`app/schemas/task.py`) exposes the following fields through
`TaskCreate`/`TaskUpdate`/`TaskRead` (`POST`/`GET`/`PATCH` all use the same
representation):

| Field | Type | Notes |
|---|---|---|
| `id` | `int` | server-assigned, read-only |
| `title` | `string` | required, 1–200 chars |
| `description` | `string \| null` | optional, up to 2000 chars |
| `status` | `"todo" \| "in_progress" \| "done"` | defaults to `"todo"`; not settable on create |
| `priority` | `"low" \| "medium" \| "high"` | defaults to `"medium"` |
| `due_date` | `date \| null` | optional, no time-of-day |
| `remind_days_before` | `int \| null` | optional, `0`–`3650`. Requires `due_date` to be set in the same request (create) or to already be set / also being set (update). A request that would leave a reminder configured with no `due_date` fails with `422` (`INVALID_REMINDER_CONFIGURATION`). **Configuring this field only persists the reminder preference — it does not cause any notification (email, push, SMS, or otherwise) to be sent. No delivery mechanism exists yet.** `null` means no reminder is configured. |
| `created_at` / `updated_at` | `datetime` | server-assigned, read-only |

## Running tests

```bash
# from this directory, with the venv active and dev deps installed
pytest
```

The suite runs against an **in-memory SQLite DB** (`tests/conftest.py`), not
Postgres — no external service needed to run tests. This is a deliberate
trade-off shared with the playbook's Bookmarks example: the model uses only
portable SQLAlchemy Core types, so behavior matches. Point `DATABASE_URL` at
a real Postgres instance and adapt `conftest.py` if you want the suite to run
against Postgres directly.

- **Unit tests** (`tests/unit/`) — `TaskService` against a fake repository,
  no DB, no app.
- **Integration tests** (`tests/integration/`) — the repository against a
  real in-memory SQLite DB, and the full app driven through `TestClient`
  (create/list/get/update/delete, status filtering, the `404`/`422` error
  envelope, health/ready).

See `../engineering-playbook/frameworks/fastapi/testing.md` for the
test-client and dependency-override patterns used here.

## Configuration

Environment variables are documented in `.env.example`. All config is read
once into the typed `Settings` object in `app/core/config.py`; nothing else
reads the environment directly.

| Variable       | Default                                                              | Meaning                 |
|----------------|-----------------------------------------------------------------------|-------------------------|
| `DATABASE_URL` | `postgresql+psycopg://task_tracker:task_tracker@localhost:5433/task_tracker` | SQLAlchemy database URL |
| `ENVIRONMENT`  | `development`                                                        | environment name        |
| `LOG_LEVEL`    | `INFO`                                                               | root log level          |

## Migrations

Schema is managed by [Alembic](https://alembic.sqlalchemy.org/), not by
`Base.metadata.create_all()` — the application no longer creates or alters
schema at startup. Migration files live in `alembic/versions/`; `alembic/env.py`
resolves its DB connection from `get_settings().database_url`, the same
`Settings` object the app itself uses, so there's no separately-maintained
connection string.

- **Fresh database:** `alembic upgrade head` applies the full history —
  currently a baseline migration creating `tasks`, followed by one creating
  `comments`. This is step 5 of "Running locally" above.
- **Existing database from before Alembic was adopted** (has `tasks`, no
  `comments`, no Alembic version tracking): stamp it at the baseline
  revision — which only records that revision as already applied, without
  running its DDL — then apply the rest of the history:
  ```bash
  alembic stamp 2baa5d553906
  alembic upgrade head
  ```
  This adds `comments` with no manual SQL and no changes to existing
  `tasks` rows. Stamping is only safe because the baseline migration was
  generated and verified to match `create_all()`'s old output exactly — if
  a database's `tasks` table has ever drifted from `app/models/task.py`
  (a hand-applied hotfix column, for example), introspect and reconcile it
  before stamping rather than assuming it matches.
- **Adding a migration for a model change:** `alembic revision --autogenerate
  -m "..."`, then hand-read the generated `upgrade()`/`downgrade()` against
  the model diff before committing — autogenerate drafts, it does not
  decide (it's known to miss things like `ondelete` behavior on some
  SQLAlchemy/Alembic version combinations). Migrations are append-only:
  correct a mistake with a new migration, never by editing one already
  merged.
- `alembic upgrade head` always runs as an explicit, separate step — never
  from inside application startup (crash-loop risk, races between workers
  booting concurrently against the same database).
- The test suite is unaffected by any of this: `tests/conftest.py`'s
  fixtures build schema directly via `Base.metadata.create_all()` against
  an in-memory SQLite engine, independent of Alembic (see "Running tests").

## Deploying

Not deployed — this is a sample application. A real service would run
`alembic upgrade head` as an explicit release step (already how this
project manages schema — see "Migrations" above), pin a production
`DATABASE_URL`, containerize the API itself, and run
`../engineering-playbook/checklists/pre-deploy.md` before any production
deploy.

## Related docs

- Project structure: `../engineering-playbook/core/project-structure.md`
- API design: `../engineering-playbook/core/api-design.md`
- Error handling: `../engineering-playbook/core/error-handling.md`
- Logging & observability: `../engineering-playbook/core/logging-observability.md`
- Configuration & secrets: `../engineering-playbook/core/configuration-secrets.md`
- FastAPI idioms / scaffold / testing: `../engineering-playbook/frameworks/fastapi/`
