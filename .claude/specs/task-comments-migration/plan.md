# Plan: Task Comments Database Migration — Milestone 3

Status: Implemented ✅ Done (2026-07-07)
Traces to: [spec.md](./spec.md)
Last updated: 2026-07-07

## Completion note

Tasks 1–5 landed together: `app/main.py`'s lifespan no longer imports or
calls `init_db()` (only its unrelated `logger.info("app_started", ...)`
call remains), `app/db/session.py::init_db()` was deleted entirely (`grep
-rn init_db app/ tests/` returns nothing), and `tests/conftest.py`'s
`client` fixture no longer takes a `monkeypatch` parameter or references
`app.main.init_db` — `db_session`'s own direct `Base.metadata.create_all(engine)`
call was already sufficient and is unchanged.

`pytest`: 51 passed, unchanged from Milestones 1–2.

Verified against a disposable scratch Postgres instance (a throwaway
`postgres:16-alpine` container on `localhost:5555`, dropped afterward —
`docker-compose.yml`'s `postgres` service was never started or touched):
- **Pre-migration:** booting the app (`uvicorn app.main:app`) against a
  completely empty scratch database and requesting `GET /v1/tasks` failed
  with `sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable)
  relation "tasks" does not exist` — confirming no implicit schema creation
  happens at startup anymore.
- **Post-migration:** running `alembic upgrade head` against that same
  database, then re-issuing the identical request, returned `200 {"data":
  []}`; a follow-up `POST /v1/tasks` returned `201` with the created task —
  confirming the migrate-then-boot workflow works end to end.

The scratch container was removed after verification.

## Prior milestones (context, not in scope here)

Milestone 1 is complete: `alembic` is a declared dependency, `alembic/env.py`
resolves its connection from `get_settings().database_url` and sees both
`Task` and `Comment` via `Base.metadata`, and a baseline migration
(`2baa5d553906`) creates `tasks` exactly as `app/models/task.py` defines it.

Milestone 2 is complete: a second migration (`8f3a500e1e75`) creates
`comments` exactly as `app/models/comment.py` defines it, chained onto the
baseline. Both migrations were verified against real Postgres — a fresh
database's full history matches `Base.metadata.create_all()`'s output
exactly, a database seeded to look like today's pre-Alembic state
transitions via stamp-then-upgrade with zero data loss, and rollback works
end to end. `pytest` passes unchanged (51 tests). See
`.claude/specs/task-comments-migration/plan.md`'s git history (commits
`318ae05`, `9a2e971`, `617e375`) for the full record of both milestones.

This document plans **only** the next slice, Milestone 3 (the "cutover"),
per the approved spec's FR5 and the Milestone 2 plan's own "Out of Scope"
deferral of this exact work.

---

## 1. Objective

Stop the application from implicitly creating or altering schema at startup
against a real database, now that Alembic fully covers both `tasks` and
`comments` (Milestones 1–2). Concretely: remove the `init_db()` call from
`app/main.py`'s startup lifespan, delete the now-dead `init_db()` function
from `app/db/session.py`, and clean up the one test fixture that exists only
to neutralize that call. This closes FR5 and the Architectural Requirements
of the spec — from this point forward, an explicit `alembic upgrade head`,
run separately from application startup, is the only thing that changes
schema outside of the test suite.

Nothing in `app/models/`, `app/services/`, `app/repositories/`, `app/api/`,
or `app/schemas/` changes as part of this milestone. Updating
`README.md`/`CLAUDE.md`'s "Migrations" sections to describe this as adopted
is Milestone 4, not here — see Out of Scope.

## 2. Implementation Tasks

Each task is small and sequential; later tasks depend on earlier ones
within this list.

1. **Remove the implicit `init_db()` call from app startup.**
   What: in `app/main.py`'s `create_app()`, delete the `init_db()` call
   inside the `lifespan` context manager and drop the now-unused
   `from app.db.session import init_db` import. The lifespan's
   `logger.info("app_started", ...)` call is unrelated to schema and stays.
   Why: this is FR5 — the actual behavior change this milestone exists to
   deliver.
   Files: `app/main.py`.
   Depends on: nothing (first slice of this milestone).

2. **Delete the now-dead `init_db()` function.**
   What: remove `init_db()` entirely from `app/db/session.py`, and update
   the module's docstring/comments that currently describe it as "fine for
   a sample app." Confirmed safe to delete outright (not deprecate): after
   Task 1 nothing calls it, and its own internal `from app import models`
   side-effect import is redundant regardless — `app/repositories/tasks.py`
   and `app/repositories/comments.py` already import `app.models.task` and
   `app.models.comment` directly at module load, which is enough to
   register both on `Base.metadata` before any `create_all()` call,
   including `tests/conftest.py`'s own direct one (see Task 3).
   Why: keeps with the project's no-dead-code convention — an unused
   function still described as a valid schema path would contradict the
   Architectural Requirement that `create_all()` is no longer relied on for
   production schema.
   Files: `app/db/session.py`.
   Depends on: Task 1.

3. **Clean up `tests/conftest.py`'s now-unnecessary monkeypatch.**
   What: remove the `monkeypatch.setattr("app.main.init_db", lambda: None)`
   line and its explanatory comment from the `client` fixture in
   `tests/conftest.py`, and drop the fixture's `monkeypatch:
   pytest.MonkeyPatch` parameter (nothing else in that fixture needs it).
   `db_session`'s own direct `Base.metadata.create_all(engine)` call is
   untouched — it already builds the SQLite schema independently of
   `init_db()`, so no test behavior changes.
   Why: this is the "matching tests/conftest.py cleanup" the Milestone 2
   plan named explicitly as deferred to this milestone — left in place,
   the monkeypatch would raise `AttributeError` once `app.main.init_db` no
   longer exists after Task 2.
   Files: `tests/conftest.py`.
   Depends on: Tasks 1 and 2.

4. **Run the existing suite.**
   What: run `pytest` and confirm all 51 tests (unchanged count) still
   pass, with none of them relying on the removed `init_db()`/monkeypatch
   machinery.
   Why: regression check — nothing in the application's request-handling
   behavior should change, only its startup path.
   Files: none.
   Depends on: Tasks 1–3.

5. **Verify the real cutover against Postgres.**
   What: against a scratch/disposable Postgres database (same
   throwaway-container discipline as Milestones 1–2 — never
   `docker-compose.yml`'s shared `postgres` service):
   (a) On a completely empty database, boot the app pointed at it via
   `DATABASE_URL` and confirm a DB-touching request (e.g. `GET /v1/tasks`)
   fails with a "relation does not exist" error rather than silently
   succeeding against tables the app itself just created.
   (b) Run `alembic upgrade head` against that same database, re-issue the
   identical request, and confirm it now succeeds — proving the intended
   new workflow (migrate explicitly, then boot) works end to end.
   Why: FR5 and the Architectural Requirements are claims about real
   deployment behavior; Milestone 2 set the bar at a runtime demonstration
   against real Postgres rather than a code read alone, and this milestone
   holds the same bar.
   Files: none (verification only, against scratch infrastructure).
   Depends on: Tasks 1–2 (code changes must exist); Milestones 1–2's
   migrations (used to bring the scratch DB to a working schema in step
   (b)).

6. **Record the verification outcome.**
   What: once Tasks 1–5 pass, append a completion note to this plan (same
   style as Milestones 1 and 2's) capturing what was checked and
   confirming only scratch/disposable infrastructure was touched.
   Why: keeps the plan's audit trail consistent, and gives Milestone 4 a
   documented, verified starting point to depend on.
   Files: `.claude/specs/task-comments-migration/plan.md` (this file,
   appended to — not part of the current planning step, done after
   implementation).
   Depends on: Tasks 1–5 all passing.

## 3. Cutover Strategy

**Delete, don't deprecate.** `init_db()` is removed outright rather than
kept around as an opt-in convenience (e.g. behind an env flag), because the
spec's Architectural Requirements are explicit that `create_all()` "must no
longer be relied upon" for production schema — keeping a working-but-unused
escape hatch would invite exactly the silent-schema-drift risk Milestones
1–2 exist to close, and it would sit as dead code the moment Task 1 lands.
Test infrastructure is unaffected: `tests/conftest.py`'s `db_session`
fixture already calls `Base.metadata.create_all(engine)` directly against
its own SQLite engine, not through `init_db()`, so it needs no equivalent
replacement — only the now-pointless monkeypatch of `app.main.init_db` goes
away (Task 3).

**One explicit cutover point, not a gradual one.** Milestone 2's plan
flagged the risk of `create_all()` and Alembic both being live against the
same database during the transition window; this milestone closes that
window in a single commit — Tasks 1 and 2 land together, so there is never
a state where `init_db()` exists but is silently unused, or where the
lifespan still calls it after the function is gone.

**Sequencing gap with Milestone 4 is accepted, not hidden.** After this
milestone, `README.md`'s "Run locally" instructions (`docker compose up -d
postgres` then `uvicorn app.main:app --reload`) no longer produce a working
schema on a fresh Postgres volume, because they don't yet mention running
`alembic upgrade head` first. The Milestone 2 plan already named the docs
update as Milestone 4's job, not this milestone's; this is called out again
here as a live consequence (see Risks), and is intentionally not patched
early, so Milestone 4 has a concrete, reproducible gap to close rather than
a hypothetical one.

## 4. Testing Strategy

- **Existing suite (regression only):** `pytest` runs unchanged and must
  stay green. Per `core/testing-strategy.md` and this project's own
  documented split, this is necessary but not sufficient evidence for this
  milestone — the suite runs entirely on SQLite via `tests/conftest.py`'s
  fixtures, which never call `init_db()` or hit a real Postgres startup
  path, so it cannot by itself prove the cutover actually changed
  production behavior.
- **Real Postgres verification (the actual evidence):** against a scratch
  Postgres database, the two-step check in Task 5 — empty DB fails a
  DB-touching request pre-migration, the identical request succeeds
  post-`alembic upgrade head` — is what actually proves FR5. This mirrors
  Milestones 1–2's standard of demonstrating behavior against a real
  database rather than asserting it from a code read.
- **No new automated test is added.** There is no application-level
  behavior to unit- or integration-test here (the change is entirely to
  the startup lifespan and one test fixture, not to any request-handling
  code path) — `tests/conftest.py`'s existing fixtures already cover the
  "does the app work against a DB with the right schema" case, and will
  keep doing so unchanged after Task 3.
- All scratch/seed databases used for Task 5 are dropped after
  verification; `docker-compose.yml`'s shared `postgres` service/volume is
  never used as a stand-in for either state in Task 5.

## 5. Acceptance Criteria

- [x] `app/main.py`'s lifespan no longer calls or imports `init_db()` —
      application startup performs no schema DDL against a real database.
      (FR5)
- [x] `app/db/session.py::init_db()` is deleted — `grep -rn init_db app/`
      returns no results.
- [x] `tests/conftest.py`'s `client` fixture no longer references
      `app.main.init_db` (that attribute no longer exists after the above);
      `db_session`'s direct `Base.metadata.create_all(engine)` call is
      unchanged.
- [x] `pytest` (full existing suite, 51 tests) passes unchanged.
- [x] Against a real, empty scratch Postgres database, booting the app and
      issuing a DB-touching request fails with a "relation does not exist"
      error — confirmed by direct observation, not inferred from a
      successful `alembic` run elsewhere. (FR5)
- [x] Running `alembic upgrade head` against that same scratch database and
      re-issuing the identical request succeeds — confirming the
      migrate-then-boot workflow works end to end. (FR5)
- [x] No change to `app/models/`, `app/services/`, `app/repositories/`,
      `app/api/`, or `app/schemas/` — this milestone touches only the
      startup/schema-bootstrap path and its one test fixture.
- [x] Every Postgres check above was run against a disposable scratch
      database that is dropped afterward — no shared local database with
      real data was used, and nothing in this milestone touched a
      staging/production environment.

## 6. Risks and Assumptions

- **Sequencing gap with Milestone 4's documentation.** `README.md`'s "Run
  locally" section will, after this milestone, no longer produce a working
  schema on a fresh `docker-compose.yml` Postgres volume without a
  now-undocumented `alembic upgrade head` step. This is an accepted,
  explicitly-named consequence (see Cutover Strategy) — Milestone 2's plan
  already deferred the docs update to Milestone 4, and this milestone does
  not pull that work forward.
- **Local dev workflow change.** Any developer used to `create_all()`
  silently keeping a local Postgres schema in sync with model changes loses
  that convenience — after this milestone, a local Postgres environment
  needs `alembic upgrade head` (or a fresh `downgrade base` + `upgrade
  head`) after every schema-affecting model change, exactly like
  production. Not a defect, but a workflow change worth surfacing since
  it's easy to be surprised by mid-development, before Milestone 4's docs
  land.
- **Already-running local/shared Postgres databases are not touched or
  checked by this milestone.** A developer's existing
  `docker-compose.yml`-backed database that was built via the old
  `create_all()` path, and has never had Milestone 2's stamp-then-upgrade
  procedure run against it, will still boot the app successfully after
  this change (nothing forces a migration check at startup) — but its
  schema is correct by history, not by Alembic tracking. That gap is a
  manual step for whoever owns that database; this milestone doesn't force
  or automate it (matches the spec's Non-goals around not building a
  general CI/tooling program).
- **No startup-time guard rail added.** This milestone does not add a
  "refuse to boot if migrations are pending" check (e.g. comparing
  `alembic_version` against head) before serving traffic. Not required by
  FR5, and out of scope per the spec's Non-goals — flagged here so it isn't
  mistaken for an oversight.

## 7. Out of Scope

- Updating `README.md`'s and `CLAUDE.md`'s "Migrations" sections to
  describe Alembic as adopted, including documenting the now-required
  `alembic upgrade head` step for a fresh local environment — Milestone 4.
- Any change to `app/models/`, `app/services/`, `app/repositories/`,
  `app/api/`, or `app/schemas/` — this milestone is startup/schema-bootstrap
  cutover only.
- Adding a startup-time or CI check that verifies the database is at
  `head` before serving traffic — not required by FR5 (spec Non-goals).
- Migrating, stamping, or otherwise touching any actual pre-existing
  local/shared Postgres database (e.g. a developer's `docker-compose.yml`
  volume) — this milestone changes application code and verifies behavior
  only against disposable scratch databases, per the same discipline as
  Milestones 1 and 2.
