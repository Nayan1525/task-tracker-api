# Plan: Task Comments Database Migration — Milestone 2

Status: Implemented ✅ Done (2026-07-06)
Traces to: [spec.md](./spec.md)
Last updated: 2026-07-06

## Completion note (Task 6)

`alembic/versions/8f3a500e1e75_add_comments_table.py` was generated via
autogenerate against a scratch Postgres database already upgraded to the
Milestone 1 baseline (`2baa5d553906`) — autogenerate detected only the
missing `comments` table and its `ix_comments_task_id` index, correctly
capturing the `task_id → tasks.id` foreign key with `ondelete='CASCADE'`.
Hand-review against `app/models/comment.py` found the generated file
already matched the model exactly (column-for-column, same as how
`created_at`'s Python-side `default=` correctly produces no DDL default,
consistent with the baseline migration's treatment of `Task`'s
timestamp columns) — no trimming or correction was needed, unlike
Milestone 1's baseline.

Verified against a disposable scratch Postgres instance (a throwaway
`postgres:16-alpine` container on `localhost:5544`, separate from
`docker-compose.yml`'s `postgres` service to avoid touching any
shared/local database):
- **Fresh database:** `alembic upgrade head` against an empty database
  produced `tasks` and `comments` byte-for-byte identical (via `\d`
  introspection) to a separate `Base.metadata.create_all()` scratch
  database — same columns, types, nullability, defaults,
  `ix_tasks_status`, `ix_comments_task_id`, and the cascade FK. `alembic
  check` against the migrated database reported "No new upgrade
  operations detected," confirming no model/migration drift.
- **Existing pre-Alembic database:** a scratch database was seeded by
  applying only the baseline migration's `upgrade()` (`alembic upgrade
  2baa5d553906`) and then dropping the `alembic_version` table it
  created, reproducing "has `tasks`, no `comments`, no Alembic
  bookkeeping." Two rows were inserted into `tasks` and their MD5
  checksum recorded. Confirmed beforehand: no `comments` table, zero
  `comments` rows. `alembic stamp 2baa5d553906` recorded the baseline as
  applied without running any DDL (no upgrade log line for it), then
  `alembic upgrade head` ran only the `comments` migration. Result:
  `comments` created correctly (0 rows), and the `tasks` rows' checksum
  was identical before and after — no data loss, no manual SQL.
- **Rollback:** from the fully-upgraded fresh database, `alembic
  downgrade -1` dropped `comments` cleanly (FK respected), and `alembic
  downgrade base` then dropped `tasks` cleanly — no constraint or index
  errors at either step.
- `pytest`: 51 tests passed, unchanged from Milestone 1's count — nothing
  in `app/` or `tests/` was touched.

All scratch databases and the throwaway container were dropped/removed
after verification; `docker-compose.yml`'s `postgres` service and its
volume were never started or touched during this milestone.

## Prior milestone (context, not in scope here)

Milestone 1 is complete: `alembic` is a declared dependency
(`pyproject.toml`), `alembic.ini` carries no static `sqlalchemy.url`,
`alembic/env.py` resolves the connection from `get_settings().database_url`
and sets `target_metadata = Base.metadata` via an `app.models` import (so
both `Task` and `Comment` are visible to autogenerate), and a baseline
migration (`alembic/versions/2baa5d553906_baseline_tasks_table.py`) creates
`tasks` exactly as `app/models/task.py` defines it — verified against a real
Postgres instance to match `Base.metadata.create_all()`'s output
column-for-column, with a clean downgrade. `pytest` passes unchanged. This
document plans **only** the next slice, Milestone 2, per the approved
plan's sequencing (`comments` migration + existing-database transition,
depends on Milestone 1).

---

## 1. Objective

Add the second Alembic migration — creating `comments` exactly as
`app/models/comment.py` defines it, depending on the Milestone 1 baseline —
and prove, against a real Postgres instance, that a database created before
Alembic existed (has `tasks`, has no `comments`, has no Alembic version
tracking) can adopt Alembic and gain `comments` with zero data loss and no
hand-written SQL. This closes FR1–FR4 of the spec in full: a fresh database
and an already-running one both end up in the same place — full migration
history applied, schema matching the ORM models exactly.

Nothing in `app/`, `tests/`, `README.md`, or `CLAUDE.md` changes as part of
this milestone — those are Milestone 3 (cutover) and Milestone 4
(documentation).

## 2. Implementation Tasks

Each task is small and sequential; later tasks depend on earlier ones
within this list.

1. **Author the `comments` migration.**
   What: generate a new revision via Alembic autogenerate, run against a
   scratch Postgres database that already has the Milestone 1 baseline
   applied (so the only diff autogenerate can see is the missing
   `comments` table) — then hand-read the generated `upgrade()`/
   `downgrade()` against `app/models/comment.py` before it is treated as
   final. Confirm it declares `down_revision = "2baa5d553906"` (chains onto
   the baseline, not a second root) and reproduces every column (`id`,
   `task_id`, `author`, `message`, `created_at`), the
   `task_id → tasks.id` foreign key with `ondelete="CASCADE"`, and
   `ix_comments_task_id`.
   Why: this is the actual persistence deliverable of the whole
   task-comments-migration effort — everything else in this milestone
   exists to prove it's safe to apply.
   Files: creates `alembic/versions/<new_rev>_add_comments_table.py`.
   Depends on: Milestone 1's baseline migration existing and being applied
   to the scratch DB used for autogeneration.

2. **Verify the full history against a fresh, empty database.**
   What: against a throwaway Postgres database with no tables at all, run
   the complete migration history (baseline, then the new `comments`
   migration) and introspect the result — every column, type, nullability,
   default, `ix_tasks_status`, `ix_comments_task_id`, and the FK/cascade —
   against both the two model files and a separately-built
   `Base.metadata.create_all()` scratch database, the same
   cross-check method Milestone 1 used for `tasks` alone.
   Why: this is FR1 — proves the "fresh database" path is complete and
   correct once both migrations exist together, not just that each
   migration runs without raising.
   Files: none (verification only, against scratch infrastructure).
   Depends on: Task 1.

3. **Seed a scratch database that reproduces today's real pre-Alembic
   state.** What: build a throwaway Postgres database containing a
   `tasks` table but nothing else — no `comments` table, no
   `alembic_version` table — the same shape any real Postgres database
   run before this feature existed. Then explicitly confirm it: query for
   a `comments` table (must not exist) and, if present, zero rows;
   confirm no `alembic_version` table exists. See Migration Strategy below
   for exactly how this table is produced without accidentally also
   creating `comments`.
   Why: turns the spec Review gate's first non-blocking note (no
   `comments` data exists anywhere yet) into a checked precondition
   instead of an assumption, before the transition procedure is exercised
   against anything.
   Files: none (scratch database only).
   Depends on: Milestone 1's baseline migration (used to build the seed).

4. **Exercise the stamp-then-upgrade transition.**
   What: against the seeded database from Task 3, stamp it at the baseline
   revision (recording that revision as already applied, without running
   its DDL — the table already exists and already matches it), then apply
   the rest of the history (the Task 1 migration). Confirm the result:
   `comments` now exists with the right shape, the pre-existing `tasks`
   rows are byte-for-byte unchanged, and no SQL was hand-written at any
   point.
   Why: this is FR2 and FR3's forward direction — the concrete mechanism
   the spec deferred to planning, now proven rather than assumed.
   Files: none (verification only).
   Depends on: Tasks 1 and 3.

5. **Verify rollback of the full history.**
   What: from the fully-upgraded state (either scratch database from Task
   2 or 4), roll back one step (drops `comments`, respecting its FK to
   `tasks`) and confirm no constraint/index error, then roll back again
   (drops `tasks`) and confirm the database is empty of both tables.
   Why: FR3's reverse direction — reversibility was asserted in the spec
   but only proven for `tasks` alone in Milestone 1; this proves it for
   the combined history.
   Files: none (verification only).
   Depends on: Task 2 (or 4).

6. **Record the verification outcome.**
   What: once Tasks 1–5 pass, append a completion note to this plan (same
   style as Milestone 1's, in the approved multi-milestone plan) capturing
   the new revision ID, what was checked, and confirmation that scratch
   databases were dropped afterward and no real/shared database was
   touched.
   Why: keeps the plan's audit trail consistent with how Milestone 1 was
   closed out, and gives Milestone 3 a documented, verified starting
   point to depend on.
   Files: `.claude/specs/task-comments-migration/plan.md` (this file,
   appended to — not part of the current planning step, done after
   implementation).
   Depends on: Tasks 1–5 all passing.

## 3. Migration Strategy

**Producing the `comments` migration.** Generated via autogenerate, the
same method Milestone 1 used for the baseline — but critically, run against
a database that is *already at the baseline revision*, not an empty one.
Diffing from empty would let autogenerate re-propose `tasks` alongside
`comments`; diffing from "baseline already applied" leaves exactly one
table for it to find. The generated file is then hand-read against
`app/models/comment.py` column-by-column (per the spec's "autogeneration
drafts, it does not decide" rule) before being treated as committable —
specifically checking the FK's `ondelete="CASCADE"` made it into the
generated `sa.ForeignKeyConstraint`/`sa.Column` call, since that detail is
easy for autogenerate to drop silently on some SQLAlchemy/Alembic version
combinations.

**Transitioning an existing pre-Alembic database.** The mechanism is
stamp-then-upgrade: `alembic stamp <baseline-revision>` writes a row into
Alembic's `alembic_version` bookkeeping table recording that revision as
already applied, without executing that revision's `upgrade()` DDL. This is
safe here specifically because Milestone 1's baseline migration was
generated (and verified) to produce a `tasks` table byte-for-byte identical
to what `create_all()` already put there — stamping is only valid because
the existing table's actual shape and the migration's assumed starting
shape are the same thing, not a coincidence being relied on blindly. After
stamping, `alembic upgrade head` runs every migration after the stamped
revision — here, just the new `comments` migration — against the real
connection. No manual SQL, no dropped/recreated `tasks` table, no touched
`tasks` rows.

To build the Task 3 seed database (a stand-in for a real pre-Alembic
environment) without accidentally reproducing today's codebase's `create_all()`
behavior — which would create `comments` too, since the `Comment` model
already exists in `app/models` — the seed is built by applying *only* the
baseline migration's `upgrade()` (`alembic upgrade 2baa5d553906`) to an
empty scratch database, then dropping the `alembic_version` table that
command creates as a side effect. That reproduces exactly what a real
pre-Alembic environment has: a `tasks` table matching today's model, and
no Alembic bookkeeping at all — without requiring the codebase to
temporarily "forget" the `Comment` model to simulate history.

**Verifying against the SQLAlchemy models.** Two independent checks, not
one: (1) direct schema introspection of the post-migration database
(columns, types, nullability, server defaults, indexes, FK definition)
read side-by-side against `app/models/task.py` and `app/models/comment.py`;
(2) running Alembic's own autogenerate diff against the fully-migrated
database and confirming it reports no pending changes — if the migration
history and the model metadata have drifted, autogenerate will propose
something. Neither check alone is treated as sufficient — (1) catches
things autogenerate is known to miss (e.g. exact `CHECK` constraint text
for the `native_enum=False` enum columns), (2) catches anything a human
reading of the migration file might have missed.

## 4. Testing Strategy

All of this milestone's real verification happens against Postgres
(docker-compose's `postgres` service, or an equally throwaway Postgres
database/container) — per the approved plan's Sequencing principle,
`pytest` runs on SQLite and cannot exercise Alembic at all, so a green
suite is necessary but never sufficient evidence for this milestone.

- **Fresh database:** build an empty scratch Postgres database, apply the
  full history (`alembic upgrade head`), and introspect it against both
  models and against a separate `Base.metadata.create_all()` scratch
  database, per Task 2. Then roll the same database all the way back
  (`alembic downgrade base`) and confirm it ends up with neither table.
- **Existing pre-Alembic database:** build the Task 3 seed (baseline DDL
  applied directly, `alembic_version` table then dropped to simulate "no
  Alembic here yet"), explicitly confirm zero `comments` rows/table before
  touching it, then run stamp-then-upgrade (Task 4) and confirm `tasks`
  rows are untouched and `comments` now exists correctly.
- **Rollback verification:** from a fully-upgraded scratch database,
  `alembic downgrade -1` must drop `comments` cleanly (its FK to `tasks`
  does not block dropping the child table), and a further downgrade must
  drop `tasks` — both checked for the absence of any constraint/index
  error, not just a non-zero exit code.
- **Existing suite:** run `pytest` unchanged and confirm it's still fully
  green. This is a regression check (nothing in `app/` changed, so nothing
  should break) — it is explicitly *not* evidence that the migrations
  themselves are correct, since the suite never touches Alembic or
  Postgres.
- No change to `tests/conftest.py`, `tests/factories.py`, or any existing
  test file is needed or made — the spec's Non-goals keep the test schema
  strategy untouched, and this milestone doesn't touch application code at
  all.

All scratch/seed databases are dropped after verification; no shared local
Postgres data (e.g. a developer's default `task_tracker` database with real
rows) is used as a stand-in for "existing pre-Alembic database" — a
separate, disposable database name is used for every check in this
milestone.

## 5. Acceptance Criteria

- [ ] `alembic/versions/<new_rev>_add_comments_table.py` exists, chains
      onto the Milestone 1 baseline (`down_revision = "2baa5d553906"`), and
      was hand-reviewed against `app/models/comment.py` before being
      treated as final — not committed as raw autogenerate output.
- [ ] Applying the full migration history to a fresh, empty Postgres
      database produces `tasks` and `comments` matching
      `Base.metadata.create_all()`'s output exactly — every column,
      type/default, `ix_tasks_status`, `ix_comments_task_id`, and the
      `task_id → tasks.id` FK with `ON DELETE CASCADE` — confirmed by
      direct schema introspection, not just a successful `upgrade` run.
      (FR1)
- [ ] A scratch database seeded to look like today's real pre-Alembic state
      (`tasks` present via the baseline DDL, no `comments` table, no
      `alembic_version` table) is confirmed to have zero `comments`
      rows/table before the transition is exercised against it.
- [ ] Running stamp-then-upgrade against that seeded database results in
      exactly `comments` being added, with the pre-existing `tasks` rows
      byte-for-byte unchanged and no manual SQL executed at any point.
      (FR2)
- [ ] Rolling back the full history from a fully-upgraded scratch database
      drops `comments` first, then `tasks`, with no constraint or index
      error at either step. (FR3)
- [ ] Alembic's own autogenerate diff, run against a fully-migrated scratch
      database, reports no pending changes (cross-check against the manual
      schema introspection above).
- [ ] `pytest` (full existing suite) passes unchanged.
- [ ] Every check above was run against a real Postgres instance, using
      disposable scratch databases that are dropped afterward — no shared
      local database with real data was used, and nothing in this
      milestone touched a staging/production environment.

## 6. Risks and Assumptions

- **Autogenerate context matters.** Running autogenerate against the wrong
  starting state (e.g. a completely empty database instead of one already
  at the baseline revision) would make it re-propose `tasks`, which could
  get pasted into the `comments` migration by mistake. Mitigation: always
  generate the new revision against a database already stamped/upgraded to
  baseline, and hand-read the result regardless.
- **Stamping trusts, rather than verifies, that a database's `tasks` table
  actually matches the baseline revision's assumed shape.** If some real
  environment's `tasks` table has silently drifted from what
  `app/models/task.py` currently defines (a manual hotfix column, a
  differently-named index applied by hand at some point), stamping it at
  the baseline revision would hide that drift — Alembic would consider the
  database "at baseline" without ever having checked. Mitigation for this
  milestone: the seeded scratch database used for verification is built
  *from* the baseline migration's own DDL, so this risk can't manifest in
  the scratch check by construction; it's flagged here as a precondition
  to actually introspect-and-compare (not just assume) before this
  procedure is ever pointed at any non-scratch database in the future.
- **No real `comments` data exists anywhere yet** (spec Problem Statement,
  Review gate note 1) — Task 3 turns this into a checked precondition for
  the scratch database used here, but this milestone does not audit every
  real environment that might exist; that remains an assumption for
  anything beyond this milestone's own scratch verification.
- **Shared local infrastructure.** `docker-compose.yml`'s `postgres`
  service persists data in a named volume; scratch/seed databases for this
  milestone must use distinct database names (or a separate throwaway
  container) so verification never reads or writes the default
  `task_tracker` database a developer might already be using for manual
  testing.
- **No native Postgres enum involved.** `comments` has no `SAEnum` column
  (unlike `tasks`'s `status`/`priority`), so the enum-specific autogenerate
  quirks Milestone 1 had to watch for (`native_enum=False` producing a
  `CHECK` constraint rather than a native type) don't apply here — lower
  risk for this migration than the baseline, noted so review time is
  focused on the FK/cascade behavior instead, which is the actually novel
  part.
- **No CI safety net yet** (spec Risks) — still true after this milestone;
  unchanged and not addressed here.

## 7. Out of Scope

- Removing `init_db()`/`Base.metadata.create_all()` from `app/main.py`'s
  startup lifespan, and the matching `tests/conftest.py` cleanup —
  Milestone 3.
- Rewriting `README.md`'s and `CLAUDE.md`'s "Migrations" sections, and the
  root `spec.md` / `.claude/specs/task-comments/spec.md` cross-references —
  Milestone 4.
- Any change to `app/models/task.py`, `app/models/comment.py`, or any
  service/repository/router/schema — this milestone is persistence tooling
  for the existing shape only (spec Non-goals).
- Any data migration or backfill — there is no `comments` data anywhere to
  migrate (spec Non-goals), and this milestone's own precondition check
  (Task 3 / Acceptance Criteria) confirms that for its own scratch
  verification rather than assuming it.
- A CI check, auto-generation policy, or multi-environment promotion
  pipeline for future migrations (spec Non-goals) — left as a documented,
  unaddressed risk, not built here.
- Applying any part of this transition procedure to a real
  staging/production database — this milestone's acceptance criteria are
  satisfied entirely against disposable scratch/seed databases.
