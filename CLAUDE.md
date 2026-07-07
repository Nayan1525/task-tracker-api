# Task Tracker API — CLAUDE.md

## Project Overview

A small FastAPI + Postgres CRUD API for tracking tasks (create/list/get/update/delete, plus status
filtering). Layered `routers → services → repositories → models`, Postgres via SQLAlchemy 2.x + psycopg.
This is a reference/sample service — see `spec.md` and `plan.md` for its build history and explicit
out-of-scope decisions (auth and pagination are deliberately deferred, not oversights).

## Commands

| Task | Command |
|---|---|
| Install deps | `pip install -e .` then `pip install pytest httpx` |
| Run locally | `docker compose up -d postgres` then `alembic upgrade head` then `uvicorn app.main:app --reload` |
| Run tests | `pytest` |
| Interactive API docs | `http://localhost:8000/docs` once running |

## Project Layout

```
app/
├── api/v1/routers/   # one APIRouter per resource, mounted under /v1 (tasks.py, comments.py)
├── core/             # settings, exceptions, logging
├── db/                # engine/session, Base
├── models/            # SQLAlchemy ORM models (never returned to a client): task.py, comment.py
├── schemas/           # Pydantic request/response models: task.py, comment.py
├── services/          # business logic, raises domain exceptions: tasks.py, comments.py
├── repositories/      # the only layer touching SQLAlchemy query APIs: tasks.py, comments.py
└── main.py            # app factory, middleware, exception handlers, router mounting
tests/
├── unit/               # service vs. a fake repository — no DB, no app
└── integration/        # repository + full app via TestClient, real in-memory SQLite
```

`Comment` is a child resource of `Task` (many comments to one task, DB-enforced `ON DELETE CASCADE`)
— see `.claude/specs/task-comments/spec.md` for its spec.

## Routers

- One `APIRouter` per resource under `app/api/v1/routers/`, mounted under `/v1` via `app/api/v1/__init__.py`'s
  aggregate router; unversioned infra endpoints (`/health`, `/ready`) mount directly on the app.
- `comments.py` nests one level under its parent: `APIRouter(prefix="/tasks/{task_id}/comments")`, matching the
  one-level-deep nesting convention for sub-resources. It defines only `POST`/`GET` (no `PUT`/`PATCH`/`DELETE`
  for an individual comment — comments are immutable, so the framework's default 405 applies to those methods).
- Handlers are thin and **synchronous** `def`, not `async def` — DB access here is sync SQLAlchemy, so FastAPI
  runs handlers in its threadpool (see the docstring in `app/api/v1/routers/tasks.py`). Don't make a handler
  `async def` unless it's actually awaiting something.
- A handler parses via the Pydantic schema, calls exactly one service method, and returns a schema — no direct
  DB/repository access from a router. Domain failures are raised as exceptions from the service (`NotFoundError`,
  etc.) and mapped to the response by the central handler in `app/main.py`; a router never builds its own error
  response.

## Pydantic Models

- Separate input/output schemas per resource in `app/schemas/<resource>.py`: `<Resource>Create` (all required
  fields, no server-assigned ones), `<Resource>Update` (every field `Optional`, applied via
  `payload.model_dump(exclude_unset=True)` in the service so an omitted field never overwrites existing data),
  `<Resource>Read` (`ConfigDict(from_attributes=True)`, allow-lists exactly what a client sees), `<Resource>List`
  (wraps the collection — see `TaskList.data`).
- Validate at the boundary with `Field(...)` constraints (`min_length`/`max_length`, etc.) — see
  `TaskCreate.title`/`description` — not by hand-checking in the service.
- Never return an ORM model instance directly from a router; always go through the `Read` schema.

## Dependency Injection

- Providers live in `app/api/deps.py`, layered: `get_db` (yields a request-scoped `Session`, closed in
  `finally`) → `get_task_service` (builds `TaskService(TaskRepository(db))`). A route depends on the
  top-level provider only.
- Tests override providers via `app.dependency_overrides[get_db] = ...` (see `tests/conftest.py`'s `client`
  fixture) — follow that pattern for any new provider, don't monkeypatch the module.
- Settings come from `get_settings()` (`app/core/config.py`), `@lru_cache`d.

## Migrations

- **Alembic is adopted.** Schema is managed by migrations in `alembic/versions/`, not by
  `Base.metadata.create_all()` — the app no longer creates or alters schema at startup (see `app/main.py`'s
  lifespan). `alembic/env.py` resolves its connection from `get_settings().database_url`, never a separately
  maintained URL.
- Run `alembic upgrade head` as an explicit, separate step (e.g. a release step, or manually in local dev) —
  never from inside app startup (crash-loop risk, races between workers booting concurrently).
- A schema change is a model edit in `app/models/` **and** a matching migration — `alembic revision
  --autogenerate`, then hand-read the generated `upgrade()`/`downgrade()` against the model diff before
  committing; autogenerate drafts, it does not decide. Migrations are append-only — correct a mistake with a
  new migration, never by editing one already merged.
- A database that predates Alembic (has `tasks`, no `comments`, no Alembic version tracking) transitions via
  `alembic stamp 2baa5d553906` (records the baseline as applied without running its DDL) then `alembic upgrade
  head` — see `README.md`'s "Migrations" section for the full procedure and its caveat about verifying a
  database hasn't drifted from the model before stamping it.
- The test suite is unaffected: `tests/conftest.py`'s fixtures build schema directly via
  `Base.metadata.create_all()` against SQLite, independent of Alembic.

## Testing

- **Unit** (`tests/unit/test_task_service.py`): `TaskService` against `FakeTaskRepository`, an in-memory
  stand-in with the same interface as `TaskRepository` — no DB, no app. This is where business logic and the
  not-found path are pinned exhaustively.
- **Integration** (`tests/integration/`): `TaskRepository` against a real in-memory SQLite session
  (`db_session` fixture, which builds schema directly via `Base.metadata.create_all()`), and the full app via
  `TestClient` (`client` fixture, `get_db` overridden to that same session).
- Test data comes from `tests/factories.py` (`make_task_payload` for API-driven tests, `make_task_model` for
  seeding the DB directly) — use these instead of hand-building payloads/models inline.
- The suite runs against SQLite, not Postgres, because `Task` only uses portable SQLAlchemy Core types — a
  deliberate, documented tradeoff (see `README.md`), not an oversight.

## Security

- No authentication exists on `/v1/*` — a documented, deliberate scope decision for this sample (see
  `spec.md`), not a bug. Treat adding auth as new scope, not a fix.
- Config (including `database_url`) is read once into the typed `Settings` object via `pydantic-settings` —
  never read `os.environ` directly elsewhere, never hardcode a credential.
- All external input goes through a Pydantic schema — never hand-parse `request.json()` or accept an
  unvalidated query param.

## Git & Commit Conventions

- This repo currently has no commit history (a fresh sample) — don't infer conventions from `git log`; follow
  this file instead.
- Never commit `.env` (git-ignored) or hardcode a credential from it.

## Environment & Secrets

- All config comes from environment variables (see `.env.example` and `app/core/config.py`), with defaults
  matching `docker-compose.yml` for local dev. Document any new required variable in `.env.example`.

## Agent Do's and Don'ts

- Do run `pytest` after any change before considering it done.
- Do match the existing layering (router → service → repository → model) exactly for any new resource — don't
  collapse layers "for simplicity."
- Don't add authentication, pagination, or other features `spec.md` marks out-of-scope without calling it out
  as new scope, not a fix.
- Don't introduce a new dependency/pattern without flagging it first.
- Don't ship a model change without a matching, hand-reviewed Alembic migration — see "Migrations" above.
