# Implementation Review: Task Comments Database Migration

Reviewer role: Staff Software Engineer — final planning and implementation review
Review date: 2026-07-07
Documents reviewed: [`spec.md`](./spec.md), [`plan.md`](./plan.md)
Code reviewed: `alembic/`, `app/main.py`, `app/db/session.py`, `tests/conftest.py`,
`README.md`, `CLAUDE.md`, `spec.md` (root), `.claude/specs/task-comments/spec.md`,
git history `318ae05`..`5fbd3d0`

This document is a retrospective review of completed, merged work. It does not
modify any code, spec, or plan file.

---

# Feature Summary

**Overview.** This feature replaces the project's original schema-bootstrap
mechanism — `Base.metadata.create_all()` called from the FastAPI startup
lifespan — with Alembic-managed, version-controlled migrations. It was
triggered by the addition of the `Comment` sub-resource
(`.claude/specs/task-comments/`), which was shipped with model/repository/
service/router code but deliberately no migration tooling, leaving two tables
(`tasks`, `comments`) with no way for an already-running Postgres database to
safely gain the second one.

**Business goal.** Remove a scaling ceiling that was explicitly called out as
temporary from the project's inception (`README.md`'s original "Migrations"
section and `spec.md`'s Open Questions both named Alembic adoption as "the
natural next step" before this work began). The concrete goal was not new
product functionality — it was making the existing `tasks`/`comments` schema
safe to evolve going forward, for any database that has real rows in it.

**Architectural overview.** Alembic is now the single source of truth for
production schema, wired through `alembic/env.py` to the application's own
`Settings` object (`get_settings().database_url`) rather than a duplicated
connection string. Two linear migrations exist: a baseline
(`2baa5d553906`) capturing `tasks` as it already existed, and a follow-up
(`8f3a500e1e75`, `down_revision = 2baa5d553906`) adding `comments` with its
`ON DELETE CASCADE` foreign key. The test suite is deliberately kept outside
this system: `tests/conftest.py` builds schema directly via
`Base.metadata.create_all()` against in-memory SQLite, a split documented as
intentional in both the spec and `CLAUDE.md`.

---

# Implementation Timeline

The work was executed as four sequential milestones, each landed as its own
commit, matching `plan.md`'s per-milestone documents exactly.

## Milestone 1 — Alembic bootstrap + baseline migration

**Objective.** Introduce Alembic as the project's migration tool and capture
the existing `tasks` table as a "day zero" baseline, without touching
`comments` yet.

**Tasks completed.**
- Added `alembic` as a declared dependency (`pyproject.toml`).
- Generated `alembic.ini` with no static `sqlalchemy.url`.
- Wrote `alembic/env.py` to resolve the DB connection from
  `get_settings().database_url` and import `app.models` so both `Task` and
  `Comment` register on `Base.metadata` for autogenerate.
- Generated a baseline migration via `alembic revision --autogenerate`
  against an empty scratch Postgres database, then **hand-trimmed** it: raw
  autogenerate output proposed `comments` too (since `Comment` already
  existed in the codebase), and that table was deliberately removed from
  this migration's `upgrade()`/`downgrade()` (see the migration file's own
  comment) so the baseline captures only `tasks`.
- Verified column-for-column against a real Postgres instance with a clean
  `downgrade()`.

**Files created or modified.**
- `alembic.ini`, `alembic/README`, `alembic/env.py`, `alembic/script.py.mako`
- `alembic/versions/2baa5d553906_baseline_tasks_table.py`
- `pyproject.toml` (added `alembic` dependency)

**Dependencies.** None — first slice.

**Estimated engineering effort.** ~3–4 hours (Alembic wiring, hand-trimming
autogenerate output correctly, and Postgres verification for a first-time
setup). *Note: work was performed in a single AI-assisted session; this is
an effort estimate for the scope of work, not a measurement of elapsed
session time.*

**Risks encountered.** Autogenerate diffing against the full model metadata
(both `Task` and `Comment`) rather than an empty target would have silently
included `comments` in the baseline — avoided by hand-reading the generated
file rather than committing it raw (documented in the migration file's own
comment).

**Validation performed.** Applied to a real (non-shared) Postgres instance;
introspected against `app/models/task.py`; downgrade exercised.

**Deliverables.** A working Alembic setup and one verified, reversible
migration for `tasks`.

---

## Milestone 2 — `comments` migration + pre-Alembic transition path

**Objective.** Add the second migration for `comments`, and prove — against
real Postgres — that a database created before Alembic existed (`tasks`
present, no `comments`, no Alembic bookkeeping) can adopt Alembic without
data loss.

**Tasks completed.**
- Generated `8f3a500e1e75_add_comments_table.py` via autogenerate, run
  against a database already at the baseline revision (not an empty one) so
  autogenerate had only one table left to find. Reviewed and committed
  as-is (raw autogenerate boilerplate comments left in place, unlike
  Milestone 1's hand-trimmed baseline, since nothing needed removing).
- Verified fresh-database installs (`alembic upgrade head` on an empty DB)
  match `Base.metadata.create_all()` output exactly, including
  `ix_comments_task_id` and the cascade FK.
- Designed and exercised the **stamp-then-upgrade** transition:
  `alembic stamp 2baa5d553906` (records the baseline as applied without
  running its DDL) followed by `alembic upgrade head`, against a database
  seeded to look like a real pre-Alembic environment.
- Verified full-history rollback (`downgrade -1` then `downgrade base`)
  drops `comments` then `tasks` cleanly.
- A follow-up commit (`617e375`) independently re-ran all of the above
  verification from a fresh session against a new scratch container,
  rather than trusting the original completion note's claims on faith, and
  checked off the plan's acceptance criteria as a result.

**Files created or modified.**
- `alembic/versions/8f3a500e1e75_add_comments_table.py`
- `.claude/specs/task-comments-migration/spec.md`, `.claude/specs/task-comments-migration/plan.md`
  (added in this commit, retroactively covering Milestone 1 too — see
  Gaps Analysis)

**Dependencies.** Milestone 1 (the baseline migration and `env.py` wiring
must exist and be applied before autogenerate can see only the `comments`
diff).

**Estimated engineering effort.** ~5–6 hours across the two commits
(migration authoring, three-scenario Postgres verification, plus the later
independent re-verification pass).

**Risks encountered.** Running autogenerate against the wrong starting
state (empty vs. baseline-applied) was explicitly identified as a risk and
mitigated by generating only against a baseline-applied scratch database.
Stamping trusts rather than verifies that a real database's `tasks` table
matches the baseline's assumed shape — flagged in the plan as a risk that
holds for any *future* non-scratch use of this procedure, not resolved by
this milestone's own scratch verification.

**Validation performed.** Three independent real-Postgres scenarios (fresh
install, existing-database transition, rollback), each re-run once more
independently in `617e375`. `pytest`: 51 passed, unchanged.

**Deliverables.** A verified, reversible two-migration history and a
proven, documented (in the plan) transition procedure for pre-existing
databases.

---

## Milestone 3 — Cutover: remove implicit `create_all()` at startup

**Objective.** Stop the application from creating or altering schema
implicitly at boot, now that Alembic fully covers both tables.

**Tasks completed.**
- Removed the `init_db()` call and its import from `app/main.py`'s
  `lifespan`.
- Deleted the now-dead `init_db()` function from `app/db/session.py`
  entirely (not deprecated or flagged — removed outright).
- Removed the now-unnecessary `monkeypatch.setattr("app.main.init_db", ...)`
  from `tests/conftest.py`'s `client` fixture, along with its
  `monkeypatch` parameter.
- Verified against a real scratch Postgres database that an unmigrated
  database now fails a DB-touching request with
  `psycopg.errors.UndefinedTable: relation "tasks" does not exist`, and
  that running `alembic upgrade head` first makes the identical request
  succeed (`200`/`201`).

**Files created or modified.**
- `app/main.py`, `app/db/session.py`, `tests/conftest.py`

**Dependencies.** Milestones 1–2 (both migrations must exist and be
correct for the "migrate, then boot" workflow this milestone establishes
to actually work).

**Estimated engineering effort.** ~2–3 hours (small, surgical code change;
most of the effort is in real-Postgres behavioral verification rather than
the diff itself, which is 27 lines across three files).

**Risks encountered.** A documented, accepted sequencing gap: after this
milestone, `README.md`'s "Running locally" instructions (at the time)
still described the old `create_all()`-at-startup behavior, so following
them verbatim against a fresh Postgres volume would fail until Milestone 4
landed. This gap was deliberately not patched early so Milestone 4 had a
concrete, reproducible problem to close.

**Validation performed.** `pytest`: 51 passed, unchanged. Real-Postgres
before/after behavioral proof (not just a code read) that no implicit
schema creation occurs and that the explicit workflow works end to end.

**Deliverables.** An application that never touches schema outside of an
explicit `alembic upgrade head`, with the one test fixture that depended on
the old behavior cleaned up rather than left as a compatibility shim.

---

## Milestone 4 — Documentation cutover

**Objective.** Bring `README.md`, `CLAUDE.md`, and the two specs that
originally deferred Alembic in line with the system as it now exists.

**Tasks completed.**
- Rewrote `README.md`'s "Migrations" section (file layout, fresh-database
  path, stamp-then-upgrade transition, autogenerate-then-hand-review
  workflow, append-only convention) and its "Running locally"/"Deploying"
  sections to include the `alembic upgrade head` step.
- Rewrote `CLAUDE.md`'s "Migrations" section to match, and fixed five
  other stale spots: the "Commands" table, the "Project Overview"
  deferred-scope list, "Project Layout"'s `db/` comment, "Testing"'s
  fixture description, and "Agent Do's and Don'ts."
- Added forward `**Update:**` cross-reference notes to the root `spec.md`
  (two locations) and `.claude/specs/task-comments/spec.md` (one location),
  following an existing convention already present in `spec.md` for a
  different superseded scope item, without rewriting the original
  historical prose.
- Verified by literally executing the rewritten README steps against a
  scratch Postgres database and confirming the documented `curl` examples
  succeed.

**Files created or modified.**
- `README.md`, `CLAUDE.md`, `spec.md`, `.claude/specs/task-comments/spec.md`,
  `.claude/specs/task-comments-migration/plan.md`

**Dependencies.** Milestone 3 (the docs describe behavior that only became
true once the cutover landed).

**Estimated engineering effort.** ~2 hours (no code, but touches five
files across two different documentation conventions — living docs vs.
historical spec records — and requires a real-environment check to avoid
shipping docs that don't match reality).

**Risks encountered.** None new; this milestone's own plan explicitly
scoped out updating `prompts/` directory exercise templates that also
reference "no Alembic yet" (not named in the original Milestone 2
deferral), and the historical root `plan.md` (also not named in that
deferral) — both are still stale after this milestone, by design (see
Gaps Analysis).

**Validation performed.** `grep -rn init_db README.md CLAUDE.md` returns
nothing; `pytest`: 51 passed; the documented "Running locally" sequence
was executed end to end against a scratch database with a real request
succeeding.

**Deliverables.** Documentation that matches the shipped system, with an
explicit, auditable trail (via `**Update:**` notes) showing where the
project's own historical record was superseded.

---

# Dependency Graph

```
Milestone 1 (Alembic bootstrap + baseline)
        │
        │  baseline migration + env.py wiring must exist
        ▼
Milestone 2 (comments migration + pre-Alembic transition proof)
        │
        │  both migrations must be correct before it's safe to make
        │  them the *only* way schema gets created
        ▼
Milestone 3 (remove create_all() from startup)
        │
        │  docs can only describe the new workflow once it's real
        ▼
Milestone 4 (update README/CLAUDE.md/spec cross-references)
```

The sequencing is strictly linear and dependency-driven, not just
convenience ordering:

- **Milestone 2 depends on Milestone 1** because generating a correct
  `comments`-only migration required autogenerating against a database
  already at the baseline revision — doing it against an empty database
  would have re-proposed `tasks` into the same file (identified explicitly
  in the plan as the primary risk this ordering avoids).
- **Milestone 3 depends on Milestones 1–2** because removing the
  application's only schema-creation path is only safe once an equivalent,
  verified replacement (the full migration history) exists and is proven
  to produce the same schema.
- **Milestone 4 depends on Milestone 3** because the documentation changes
  describe *behavior*, not intent — writing "Alembic is adopted, `create_all()`
  no longer runs at startup" into `README.md` before Milestone 3 landed
  would have been documenting a fiction.

No milestone was parallelizable with another: each one changes a
precondition the next one's safety argument depends on.

---

# Architectural Decisions

**1. Alembic connection resolved from `Settings`, not `alembic.ini`.**
`alembic/env.py` calls `get_settings().database_url` rather than a static
`sqlalchemy.url` in `alembic.ini`. Trade-off: this couples `alembic`
invocations to the same environment-variable resolution as the app itself
(so `DATABASE_URL` must be set correctly in whatever shell runs `alembic`
commands), but it eliminates a second, independently-maintained connection
string that could drift from the app's actual config — judged the safer
trade-off given `core/configuration-secrets.md`'s single-source-of-truth
principle.

**2. Stamp-then-upgrade over a hand-written data migration.** For bringing
an existing pre-Alembic database under version control, the chosen
mechanism is `alembic stamp <baseline>` + `alembic upgrade head`, not a
custom script. Trade-off, explicitly named in the spec's Risks: stamping
*trusts* that the target database's actual `tasks` table matches the
baseline migration's assumed shape — it does not verify this. This is
acceptable specifically because the baseline migration was itself
generated *from* and verified *against* that exact shape (Milestone 1), so
the trust has a concrete basis for every database this project has
actually touched — but the trade-off becomes load-bearing risk the moment
this procedure is pointed at any database whose `tasks` table might have
drifted (e.g., a manually hotfixed column). The plan calls this out rather
than treating it as solved.

**3. Delete `init_db()` outright, not deprecate it.** Milestone 3 chose to
remove the function entirely rather than leave it behind an unused/no-op
path. Trade-off: this is a slightly larger, less "reversible" diff than
leaving dead code in place, but it was judged consistent with the
project's stated Architectural Requirement that `create_all()` "must no
longer be relied upon" for production schema — keeping a working-but-unused
escape hatch was assessed as inviting exactly the schema-drift risk the
whole feature exists to close.

**4. Test schema strategy left untouched (SQLite + `create_all()`), by
design.** The test suite does not run Alembic migrations at all, even
after this feature. Trade-off, acknowledged directly in the spec's Risks
("Permanent test/production schema-strategy divergence"): a future model
change could ship with a matching migration forgotten, and the SQLite test
suite would never catch it, because it builds schema from the models
directly, not from the migration history. The alternative — running
migrations against a real Postgres instance in CI — was explicitly ruled
out of scope for this feature (no CI infrastructure exists in this
repository at all).

**5. Documentation split into "living docs" (rewritten) vs. "historical
record" (cross-referenced, not rewritten).** `README.md`/`CLAUDE.md` were
edited in place; `spec.md` and the task-comments spec were given
forward-pointing `**Update:**` notes instead. This preserves an audit
trail of what was decided when, following a pattern the repository had
already established for a different superseded item, rather than
introducing a new convention.

---

# Gaps Analysis

*Every item below is directly observable in the current repository state —
none are hypothetical extrapolations.*

**Missing edge cases**
- The stamp-then-upgrade procedure has no automated or manual check that a
  real target database's `tasks` table actually matches the baseline
  migration's assumed shape before stamping. This is named as an accepted
  risk in the plan (`plan.md`'s Milestone 2 Risks), not a defect
  introduced silently — but there is no tooling anywhere in the repo (a
  script, a documented manual introspection step) to perform that check
  before running `alembic stamp` against a real, non-scratch database.
- `Task.status` and `Task.priority` use `SAEnum(..., native_enum=False)`
  with no `create_constraint=True`. Direct schema introspection (performed
  during this feature's own verification, per `plan.md`'s completion
  notes) shows the resulting columns are plain `VARCHAR` with **no CHECK
  constraint** — the database itself does not reject an invalid status or
  priority value written outside the ORM. This predates this feature (it
  is what `create_all()` already produced) and the migration correctly,
  faithfully reproduces it — but the migration also permanently
  codifies it as the schema's contract going forward, in a way that's now
  harder to casually notice than an inline model default.

**Technical debt**
- `.claude/specs/task-comments-migration/spec.md` and `plan.md` were both
  first committed in the Milestone 2 commit (`9a2e971`), not alongside
  Milestone 1. `git log --follow` on `plan.md` shows only two authoring
  commits total (`9a2e971`, then rewrites at `617e375`, `96b77a3`,
  `5fbd3d0`) — meaning Milestone 1 shipped without its own governing
  spec/plan in version control at the time. Not a functional defect, but
  it means the audit trail this project otherwise cares about (the spec
  Review-gate process) doesn't fully cover the first milestone's own
  history.
- The per-milestone `plan.md` convention **overwrites** the file at each
  new milestone (confirmed: the file currently shows only Milestone 4 in
  full, with Milestones 1–3 compressed into short prose summaries). Full
  task-level detail for Milestones 1–3 (numbered tasks, exact acceptance
  criteria) only survives in git history, not in the working tree — this
  review had to reconstruct it from commit diffs rather than reading it
  directly from `plan.md`.

**Testing gaps**
- No automated test exercises Alembic at all. `pytest`'s 51 tests run
  entirely against SQLite via `Base.metadata.create_all()`
  (`tests/conftest.py`) and never invoke `alembic upgrade`, `stamp`, or
  `downgrade`. Every migration verification performed for this feature
  (fresh install, pre-Alembic transition, rollback, `alembic check`) was
  done manually against throwaway Postgres containers during
  implementation and is not repeatable via `pytest` or any CI job — there
  is no CI job in this repository at all (`.github/` does not exist).
  A future migration could be added incorrectly and nothing in the
  automated suite would catch it.
- No test (automated or documented as a manual step) verifies the `/ready`
  endpoint's behavior against an unmigrated database. `app/api/v1/routers/health.py`'s
  `/ready` handler only executes `SELECT 1` — it would report `{"status":
  "ready"}` against a reachable-but-unmigrated Postgres instance, then the
  next real request would 500 with `UndefinedTable` (the exact failure
  mode Milestone 3 demonstrated deliberately, but only as a one-off manual
  check, not as a standing readiness guarantee).

**Documentation gaps**
- `README.md`'s "Migrations" section documents `alembic upgrade head` and
  the stamp-then-upgrade path, but never mentions `alembic downgrade` or
  its data-loss implications (dropping `comments` deletes all comment
  rows) — a rollback procedure exists and was verified during
  implementation, but it is not written down anywhere a developer would
  read it outside of `plan.md`'s internal verification notes.
- `prompts/database/generate-migration.md`, `prompts/database/optimize-query.md`,
  and `prompts/documentation/create-runbook.md` still describe "this
  project has no Alembic yet" as their working scenario. These were
  explicitly scoped out of Milestone 4 (per its own Out-of-Scope section)
  on the grounds that they're teaching/exercise templates rather than
  living documentation — but they are now factually wrong about the
  project's current state if anyone follows them literally.
- The root `plan.md` (the original five-milestone app-build plan, ✅
  complete) still says the app does "router mounting, `init_db()` on
  startup" and lists "Alembic migrations" among features "deferred and not
  planned" — both now false. This was a deliberate exclusion (not named in
  Milestone 2's deferred-to-Milestone-4 list), so it's a known, accepted
  gap rather than an oversight, but it means the root `plan.md` and
  `CLAUDE.md` currently disagree about whether Alembic is adopted.

**Deployment considerations**
- Nothing in the deployment story (there isn't one — this is documented as
  "not deployed, sample application") enforces that `alembic upgrade head`
  actually runs before a new version starts serving traffic. `README.md`
  documents it as a manual/pipeline step but there is no pre-start hook,
  init container pattern, or CI/CD gate anywhere in the repo implementing
  it.

**Migration risks**
- The two existing migrations are schema-only (`CREATE TABLE`, no data to
  move) since no `comments` rows have ever existed in a real environment
  (confirmed and explicitly checked as a precondition during Milestone 2).
  Nothing in the current migration history has been exercised against a
  scenario involving a large table, a lock-heavy `ALTER`, or actual
  production row counts — reasonable for where the project is today, but
  worth flagging since none of the verification performed so far is
  evidence about how this tooling behaves once real data volume exists.

**Maintainability concerns**
- The append-only migration convention and the "hand-review autogenerate
  before committing" rule are documented in `README.md`/`CLAUDE.md`, but
  nothing mechanically enforces either — both rely entirely on a future
  contributor (human or agent) reading and following the docs.

---

# Suggested Improvements

## High Priority

**1. Add a readiness check that reflects migration state, not just DB
connectivity.**
Reason: `/ready` currently only proves the database is reachable
(`SELECT 1`), which is exactly the condition Milestone 3 showed is
insufficient — a reachable-but-unmigrated database still causes request
failures.
Expected benefit: prevents a deploy from ever being marked "ready" while
serving traffic against a schema that doesn't match the code.
Implementation complexity: Low–Medium — compare Alembic's
`alembic_version` table (or use `alembic.runtime.migration.MigrationContext`)
against the code's known `head` revision inside the `/ready` handler.

**2. Add a CI job that runs the full migration history against a real
Postgres service container, plus `alembic check`.**
Reason: every piece of evidence that the migrations are correct today came
from manual, one-off verification during implementation; there is no
repeatable, automated guard against a future migration/model drift.
Expected benefit: turns this feature's own verification standard (real
Postgres, not just a code read) into a permanent, enforced gate instead of
a point-in-time fact.
Implementation complexity: Medium — requires introducing CI infrastructure
to a repository that currently has none, which is itself a decision beyond
this feature's original scope.

## Medium Priority

**3. Document (or tool) a pre-stamp verification step for the
stamp-then-upgrade procedure.**
Reason: stamping a real database currently requires trusting, not
checking, that its `tasks` table matches the baseline migration.
Expected benefit: closes the specific risk the plan already names but
leaves as an assumption for any future non-scratch use.
Implementation complexity: Low — a documented `\d tasks` / `alembic check`
comparison step, or a small script that diffs live schema against the
baseline migration's expected DDL before stamping.

**4. Add `alembic downgrade` and its data-loss implications to
`README.md`'s "Migrations" section.**
Reason: the rollback path is real, was verified, and is currently
undocumented for anyone outside this feature's own implementation
history.
Expected benefit: a future on-call engineer reaching for rollback
during an incident has a documented, safe procedure instead of needing to
read `plan.md`'s internal notes or the Alembic docs cold.
Implementation complexity: Low — documentation only.

**5. Reconcile the root `plan.md` and `prompts/database/*.md` references
to "no Alembic yet."**
Reason: these are the two remaining places in the repository that
actively contradict `CLAUDE.md`/`README.md`'s current, accurate
description of the system.
Expected benefit: removes the one remaining source of "which document do
I trust" ambiguity for a future contributor or agent.
Implementation complexity: Low for `plan.md` (same `**Update:**`
cross-reference pattern already used elsewhere); Low–Medium for the
`prompts/` files since they're scenario-driven and need more than a
one-line note to stay coherent as teaching material.

## Low Priority

**6. Add a `create_constraint=True` (or a Postgres-native enum) for
`task_status`/`task_priority`, via a new migration.**
Reason: the database currently has no mechanism to reject an invalid
status/priority value written outside the ORM.
Expected benefit: defense-in-depth against a future bug (a raw SQL script,
a bulk-load path, a different service writing to the same table)
inserting an invalid value.
Implementation complexity: Medium — this is a genuine schema change
requiring a new, carefully-reviewed migration (existing rows must already
satisfy the constraint), not a documentation fix, and is arguably outside
this feature's original scope (it predates the migration work entirely).

**7. Capture Milestone 1–3's full per-task detail somewhere durable.**
Reason: the per-milestone `plan.md` convention overwrites prior milestones'
detail with a short summary; full detail only survives in git history.
Expected benefit: a future reader (or this very review) wouldn't need to
reconstruct milestone-by-milestone task lists from commit diffs.
Implementation complexity: Low — e.g. an appendix file or this review
document itself serving that archival purpose going forward.

---

# Lessons Learned

- **The migration history is a strict, dependency-ordered chain of two
  files.** Any new migration must set `down_revision = "8f3a500e1e75"`
  (the current head) — never branch off the baseline directly, and never
  edit either existing migration file. A correction ships as a new
  migration, per the append-only convention now documented in both
  `README.md` and `CLAUDE.md`.
- **Autogenerate output is a draft, not a commit-ready file, and the
  starting database state matters.** Both existing migrations were
  produced by running `alembic revision --autogenerate` against a
  database already at the *expected prior* revision — running it against
  an empty or arbitrary database will re-propose unrelated tables into the
  new file. Always hand-read the result against the actual model diff
  before committing.
- **The test suite will not catch a migration/model mismatch.** `pytest`
  exercises the models directly against SQLite via `create_all()` and
  never runs Alembic. Confirming a new migration is correct requires the
  same manual real-Postgres verification pattern used throughout this
  feature (fresh install, `alembic check`, rollback) — there is currently
  no automated substitute for this.
- **`/ready` is not a migration-state check.** Passing readiness only
  means Postgres is reachable, not that the schema is at `head`. Anyone
  adding deployment automation on top of this service needs a separate,
  explicit `alembic upgrade head` gate — it will not be caught by the
  existing health/readiness endpoints.
- **`README.md`'s "Migrations" section is the canonical procedure for
  bringing any non-scratch database under Alembic**, including the
  explicit caveat that stamping trusts rather than verifies schema
  alignment — read it before pointing the stamp-then-upgrade procedure at
  any database that isn't disposable.
- **Not every document in this repository was updated.** The root
  `plan.md` and the `prompts/database/*.md` exercise templates still
  describe the pre-Alembic world by design (explicitly out of scope for
  Milestone 4) — don't treat them as current-state documentation for this
  feature.

---

# Final Assessment

| Dimension | Rating (1–5) | Justification |
|---|---|---|
| Architecture | 4/5 | Clean separation (Alembic owns production schema, tests keep their own independent path), connection resolution correctly centralized through `Settings`, linear and correctly-ordered migration chain. Loses a point for the acknowledged, unmitigated "trust, don't verify" gap in the stamp procedure and the lack of any schema-version-aware readiness signal. |
| Maintainability | 3/5 | The append-only and hand-review conventions are clearly documented in `README.md`/`CLAUDE.md`, but nothing enforces them mechanically, and two other documents in the same repository (`plan.md`, `prompts/database/*.md`) still contradict the current state — a future reader has to know which docs to trust. |
| Testability | 2/5 | Zero automated coverage of the migrations themselves; every correctness claim about the migration history rests on manual, non-repeatable verification performed once during implementation. The application-level regression suite (51 tests) is solid but structurally cannot detect a migration/model drift by design. |
| Documentation | 4/5 | `README.md` and `CLAUDE.md` are now detailed, accurate, and mutually consistent, with a real, verified example (the `curl` walkthrough) proving the documented steps work. Docked one point for the rollback procedure being undocumented in `README.md` and for the two known-stale documents left outside this feature's scope. |
| Production Readiness | 3/5 | The core mechanism (migrate explicitly, never at startup, verified transition path for existing databases) is sound and matches how a real service should manage schema. It falls short of "ready to operate" because there is no CI enforcement, no migration-aware readiness check, and no automated regression protection — all real gaps for an actual production deployment, though consistent with this repository's own explicit framing as a sample/reference service, not a production system. |

**Overall recommendation.** The migration tooling itself — the two Alembic
migrations, the connection wiring, and the startup cutover — is correct,
was verified thoroughly against real Postgres at each step, and is safe to
build on. As a reference implementation demonstrating how to adopt Alembic
into an existing `create_all()`-based service, this feature succeeds at
its stated goal and its documentation is trustworthy.

It is **not**, as it stands, ready to be the migration story for a real
production system without further investment: the complete absence of
automated migration testing (no CI at all in this repository) and the
absence of any migration-state-aware readiness check are the two gaps that
would need to close first. Both are proportionate to this project's
explicit identity as a sample application rather than a production
service, and neither undermines the correctness of what was actually
built — but they should not be mistaken for solved problems simply because
they weren't in this feature's original scope.
