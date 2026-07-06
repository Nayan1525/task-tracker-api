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

# 5. run the service (creates tables on startup — see "Migrations" below)
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

This sample creates tables on startup via `Base.metadata.create_all()`
(`app/db/session.py:init_db`) for simplicity — fine for local development,
not for a real service with production data. The natural next step before
this becomes more than a sample is to introduce Alembic and replace the
startup `create_all()` with `alembic upgrade head` in the deploy pipeline.

## Deploying

Not deployed — this is a sample application. A real service would add
Alembic migrations (see above), pin a production `DATABASE_URL`, containerize
the API itself, and run `../engineering-playbook/checklists/pre-deploy.md`
before any production deploy.

## Related docs

- Project structure: `../engineering-playbook/core/project-structure.md`
- API design: `../engineering-playbook/core/api-design.md`
- Error handling: `../engineering-playbook/core/error-handling.md`
- Logging & observability: `../engineering-playbook/core/logging-observability.md`
- Configuration & secrets: `../engineering-playbook/core/configuration-secrets.md`
- FastAPI idioms / scaffold / testing: `../engineering-playbook/frameworks/fastapi/`
