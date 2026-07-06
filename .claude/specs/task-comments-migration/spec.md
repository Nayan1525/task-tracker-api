# Spec: Task Comments Database Migration

Status: Approved
Owner: Nayan1525
Last updated: 2026-07-06

*Scope note: this spec covers only the schema-migration tooling needed to
get the already-implemented `Comment` model (`.claude/specs/task-comments/spec.md`)
persisted through a versioned, repeatable mechanism instead of
`Base.metadata.create_all()`. It does not touch `Comment`'s fields,
behavior, API, or any other resource.*

## 1. Problem Statement

The Task Comments feature (`.claude/specs/task-comments/spec.md`) is fully
implemented — model, repository, service, router, and DB-enforced cascade
delete all exist and are covered by tests — but that implementation was
deliberately shipped without migration tooling (see
`.claude/specs/task-comments/plan.md`'s exclusions). Today, both `tasks`
and `comments` tables only come into existence via
`Base.metadata.create_all()`, called from `app/db/session.py::init_db()` at
application startup (`app/main.py`'s lifespan). `CLAUDE.md`'s own
"Migrations" section and the root `README.md` already document why this
doesn't hold up outside a fresh sample database: `create_all()` only
creates tables that don't exist yet, never alters an existing table, has no
version history, and has no rollback — and both documents name introducing
Alembic as the specific next step once a second table needs to be added to
an environment that already has the first. That moment is now: any
Postgres database that was already running this app before comments
existed has a `tasks` table with no way to safely gain a `comments` table
short of hand-written SQL or another blind `create_all()` call.

## 2. Goals

- Introduce Alembic as this project's schema-migration tool, exactly as
  anticipated by `README.md`'s existing "Migrations" section and
  `CLAUDE.md`'s "If Alembic is introduced..." guidance — not a new
  direction, but the previously-deferred one now being taken.
- Produce a versioned migration history that, run against an empty
  Postgres database, results in a schema identical to what
  `Base.metadata.create_all()` produces today for `tasks` and `comments` —
  same columns, types, defaults, indexes, and the `comments.task_id`
  foreign key with `ON DELETE CASCADE`.
- Existing databases created before Alembic adoption must be able to
  transition to Alembic version management without data loss — this
  covers any Postgres database that already has `tasks` from the
  pre-Alembic `create_all()` era but not `comments`.
- Stop the application from implicitly creating or altering schema at
  startup against a real database, replacing that with an explicit,
  separate migration step, per `CLAUDE.md`'s existing instruction that
  this "never [runs] from inside app startup."
- Leave the test suite's schema strategy untouched — SQLite +
  `Base.metadata.create_all()` via `tests/conftest.py` fixtures keeps
  working exactly as it does today.

## 3. Non-goals

- **Not a model or behavior change.** `app/models/task.py` and
  `app/models/comment.py` are not redesigned, and the migration must
  capture exactly what they already define — this is persistence tooling
  for existing shape, not a schema redesign.
- **Not a service, repository, router, or schema change.** Nothing in
  `app/services/`, `app/repositories/`, `app/api/`, or `app/schemas/`
  changes as part of this work.
- **Not a data migration.** No `comments` rows exist anywhere yet (the
  feature has code but, per the Problem Statement, no migrated schema in
  any real environment), so there is no data to backfill or transform.
- **Not a change to how tests build schema.** `tests/conftest.py`'s
  SQLite/`create_all()` fixtures, and the `client` fixture's existing
  no-op of `init_db()`, are unaffected — this remains the documented,
  deliberate test/production schema-strategy split.
- **Not a general CI/tooling program.** No CI check that fails a PR for a
  model change missing a matching migration, no auto-generation policy
  document, no multi-environment (staging/prod) promotion pipeline — just
  enough Alembic setup and migrations to get `tasks` and `comments` under
  version control.
- **Not introducing authentication, pagination, or any other feature**
  `CLAUDE.md`/root `spec.md` mark as deferred — unrelated to this work.

## 4. Functional Requirements

- FR1: Applying the full migration history to an empty Postgres database
  creates the `tasks` table (all columns, `task_status`/`task_priority`
  enums-as-strings, `ix_tasks_status`) and the `comments` table (all
  columns, `ix_comments_task_id`, the `task_id → tasks.id` foreign key with
  `ON DELETE CASCADE`) — matching `app/models/task.py` and
  `app/models/comment.py` exactly.
- FR2: A Postgres database that already has a `tasks` table (created by
  today's `create_all()` startup path) and no `comments` table can be
  brought under Alembic's version management and end up with `comments`
  added, with no manual SQL and zero changes to existing `tasks` rows —
  i.e., no data loss during the transition.
- FR3: Migrations are reversible — rolling back past the `comments`
  migration removes `comments` (respecting its FK to `tasks`) without
  error; rolling back further removes `tasks`.
- FR4: Alembic resolves its database connection from the project's
  existing `Settings`/`get_settings()` (`DATABASE_URL`) — never a
  hardcoded URL or a second, separately-maintained connection string.
- FR5: Once Alembic is adopted, the application no longer creates or
  alters schema implicitly at startup against a real (non-test) database —
  an explicit migration step, run separately from application startup, is
  the only thing that changes schema outside of the test suite.

## 5. Technical Requirements

- Add `alembic` as a declared dependency in `pyproject.toml` — flagged
  explicitly here, per `CLAUDE.md`'s "don't introduce a new dependency ...
  without flagging it first"; this spec is that flag, and approval of this
  spec is approval of the dependency.
- Introducing Alembic means establishing the full migration
  infrastructure, not just adding the dependency: an `alembic.ini`
  configuration file, an `alembic/` directory, an `env.py` that wires
  Alembic into this project's runtime, and the migration configuration
  needed for Alembic to run against this codebase.
- That `env.py` integrates with this project's existing SQLAlchemy
  metadata — it must see both `Task` and `Comment` via `app.db.session.Base`
  — and resolves the connection at runtime from `get_settings().database_url`
  rather than a static value duplicated in `alembic.ini`.
- Migrations are written and validated against Postgres/psycopg semantics
  only — Postgres is the only engine Alembic ever runs against in this
  project; the test suite does not execute migration scripts, so SQLite
  compatibility of the migration code itself is not a requirement.
- `app/db/session.py::init_db()` and its call from `app/main.py`'s startup
  lifespan are updated to stop creating/altering schema for a real
  deployment, consistent with the Architectural Requirements below —
  `tests/conftest.py`'s `client` fixture already no-ops `init_db()`, so
  this change has no effect on the test suite.
- Update, not rewrite, the existing "Migrations" sections in `README.md`
  and `CLAUDE.md` — both already describe Alembic as the target end-state;
  they need to describe it as adopted.

## 6. Architectural Requirements

- Alembic becomes the authoritative mechanism for managing the production
  database schema — from this point forward, the source of truth for what
  schema a real deployment should have is the migration history, not the
  ORM model metadata.
- `Base.metadata.create_all()` must no longer be relied upon for creating
  or evolving the production schema. Its current role — the only thing
  that has ever brought `tasks` or `comments` into existence outside of
  tests — ends with this feature.
- Test infrastructure may continue using `create_all()` unless changed by
  a future feature — `tests/conftest.py`'s SQLite fixtures are exempt from
  this shift, per the Non-goals and the existing test/production
  schema-strategy split documented in `CLAUDE.md`.

## 7. Migration Requirements

- A baseline migration reflecting the current `tasks` table exactly as
  `app/models/task.py` defines it today — this captures "day zero," it
  does not change `Task`.
- A second migration, depending on the baseline, that creates `comments`
  exactly as `app/models/comment.py` defines it — this is the actual
  persistence work this mini-feature exists to deliver.
- Existing databases created before Alembic adoption must be able to
  transition to Alembic version management without data loss — an
  existing pre-Alembic Postgres database (`tasks` present, `comments`
  absent) must end up under Alembic's management with its existing
  `tasks` rows untouched and `comments` added. The specific mechanism for
  this transition is an implementation decision to be made and verified
  during planning, not fixed here.
- Migration history is treated as append-only from this point forward —
  no editing a migration already merged to the default branch; a
  correction ships as a new migration.
- No autogenerated migration is committed without a human reading the
  generated operations against the actual model diff first — autogeneration
  drafts, it does not decide.

## 8. Acceptance Criteria

- Applying the full migration history to a fresh, empty Postgres database
  produces `tasks` and `comments` with every column, type/default, the
  `ix_tasks_status` and `ix_comments_task_id` indexes, and the
  cascade-delete foreign key — verified against the actual database
  schema, not just "the app boots."
- Starting from a Postgres database seeded to look like today's
  pre-migration state (only `tasks` present, no Alembic version tracking),
  the transition to Alembic version management (Migration Requirements)
  results in exactly the `comments` table being added, with the
  pre-existing `tasks` rows untouched — no data loss.
- Rolling back the full migration history drops both tables cleanly with
  no constraint or index errors.
- `pytest` passes unchanged — the existing SQLite unit/integration suite
  runs exactly as before, confirming the test/production schema-strategy
  split (Non-goals, Architectural Requirements) held.
- A new contributor can get a working schema on a fresh database by
  following the project's documented setup, without hand-writing any SQL.
- Code review confirms `app/main.py`'s startup path no longer silently
  creates or alters schema against a real database, and that
  `Base.metadata.create_all()` is no longer relied upon for the production
  schema (Architectural Requirements).
- `README.md` and `CLAUDE.md`'s "Migrations" sections describe Alembic as
  adopted (not as a future step), covering both a fresh database and an
  existing pre-Alembic one.

## 9. Risks

- **Existing local/staging Postgres databases created via
  `create_all()`.** Anyone who has already run this app against a real
  Postgres instance has an untracked `tasks` table. If the transition
  mechanism (Migration Requirements) is implemented or applied
  incorrectly, Alembic could attempt to recreate `tasks` and fail, or its
  version tracking could diverge from what's actually applied. This needs
  a verified, documented procedure, not an assumption that every
  environment starts empty.
- **Autogenerate drift.** Auto-generating a migration by diffing live
  database state against model metadata, when run against a database that
  isn't in the state a developer assumes, can propose dropping or altering
  something unintended. Every migration produced for this feature must be
  hand-read against `app/models/task.py` and `app/models/comment.py`
  before being committed, not trusted as generated.
- **Overlap window between `create_all()` and Alembic.** Until
  `init_db()`'s startup behavior is actually changed, it's possible for
  both mechanisms to be exercised against the same database. Not
  destructive on its own (`create_all()` never alters an existing table),
  but confusing — the plan needs one explicit cutover point, not a gradual
  one.
- **Permanent test/production schema-strategy divergence.** Tests will
  keep getting their schema from `Base.metadata.create_all()` (SQLite);
  production gets it from Alembic migrations (Postgres). These are two
  independently maintained paths from now on — a future model change
  requires remembering to also write a migration, with nothing mechanical
  enforcing that they stay in sync. This was always going to be true once
  Alembic existed; this spec is the point where the risk becomes live
  rather than theoretical.
- **No CI safety net yet.** This spec does not add a check (e.g., a CI
  step that runs autogenerate and fails on an uncommitted diff) to catch a
  future model change shipped without a matching migration — left as a
  follow-up, not built here.

---

## Review gate

Approved after architectural review (scope consistency, goals/non-goals
separation, functional-requirement completeness, implementation-detail
check, success-criteria measurability, risk/assumption coverage, and
alignment with the existing project architecture) via `/approve-spec`.
Two non-blocking notes carried into the plan:

- The "not a data migration" non-goal and Migration Requirements' "no
  data loss" guarantee are written assuming no `comments` rows exist in
  any real environment yet (per the Problem Statement). The plan should
  verify this against any environment it targets before treating the
  existing-database transition as schema-only.
- The acceptance criterion about a new contributor getting a working
  schema "by following the project's documented setup" is descriptive
  rather than a hard pass/fail check; the plan should turn it into a
  concrete, checkable step once the actual setup docs are written.

Approved by: Nayan1525 (via Claude Code `/approve-spec` review)
Date: 2026-07-06
