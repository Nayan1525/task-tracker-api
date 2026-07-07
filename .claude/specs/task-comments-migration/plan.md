# Plan: Task Comments Database Migration — Milestone 4

Status: Implemented ✅ Done (2026-07-07)
Traces to: [spec.md](./spec.md)
Last updated: 2026-07-07

## Completion note

Tasks 1–5 landed together as pure documentation changes:
- `README.md`'s "Migrations" section rewritten to describe Alembic as
  adopted — file layout, the two-migration history, the fresh-database
  path, the stamp-then-upgrade transition for a pre-existing pre-Alembic
  database, the autogenerate-then-hand-review workflow for new migrations,
  and the append-only convention. "Running locally" now has an explicit
  `alembic upgrade head` step (5) before `uvicorn` (6); "Deploying"
  describes the migration step as adopted, not future.
- `CLAUDE.md`'s "Migrations" section rewritten to match, plus five stale
  spots fixed: the "Commands" table's "Run locally" row, the "Project
  Overview" deferred-scope parenthetical (Alembic removed, auth/pagination
  kept), "Project Layout"'s `db/` comment, "Testing"'s integration-test
  bullet, and "Agent Do's and Don'ts" (dropped the now-inapplicable
  "don't introduce Alembic" line, added a "ship a matching migration"
  rule).
- `spec.md`'s "Out of scope" Alembic bullet and matching Open Question,
  and `.claude/specs/task-comments/spec.md`'s "Out of Scope" Alembic
  bullet, each got a "**Update:**" cross-reference to this spec, following
  the exact precedent already in `spec.md`'s Scope section — no historical
  prose was rewritten.

`grep -rn init_db README.md CLAUDE.md` returns nothing. `pytest`: 51
passed, unchanged.

Verified against a disposable scratch Postgres instance (`postgres:16-alpine`
on `localhost:5566`, dropped afterward — `docker-compose.yml`'s `postgres`
service was never started or touched): literally ran the rewritten "Running
locally" steps — `alembic upgrade head` against the empty scratch database,
then `uvicorn app.main:app` — and the README's own documented `POST
/v1/tasks` and `GET /v1/tasks` `curl` examples returned `201` and `200`
respectively, with the created task round-tripping correctly. No
hand-written SQL at any point. (The stamp-then-upgrade transition path
documented here is the identical procedure already verified end-to-end in
Milestone 2's completion note; not re-run here.)

## Prior milestones (context, not in scope here)

Milestones 1–3 are complete and committed (`318ae05`, `9a2e971`, `617e375`,
`96b77a3`): Alembic is wired up (`alembic/env.py` resolves its connection
from `get_settings().database_url`, sees both `Task` and `Comment`), a
baseline migration (`2baa5d553906`) creates `tasks`, a second migration
(`8f3a500e1e75`) creates `comments`, and — as of Milestone 3 — the
application no longer creates or alters schema implicitly at startup:
`app/main.py`'s lifespan no longer calls `init_db()`, and
`app/db/session.py::init_db()` was deleted outright. Both a fresh database
and an existing pre-Alembic one (`tasks` present, no `comments`, no
`alembic_version`) were verified end to end against real Postgres,
including the stamp-then-upgrade transition and rollback. `pytest` passes
unchanged (51 tests) throughout.

Everything Alembic actually *does* is now correct and proven. What's left
is that the project's own documentation still describes the pre-Alembic
world: `README.md` and `CLAUDE.md`'s "Migrations" sections say "no Alembic
yet" / "the natural next step," several other spots reference the
now-deleted `init_db()`, and the root `spec.md` / `.claude/specs/task-comments/spec.md`
still list Alembic as out-of-scope/deferred. This milestone brings the
documentation in line with what's actually true today. No application or
test code changes as part of this milestone.

---

## 1. Objective

Update every piece of project documentation that describes schema
management as `create_all()`-at-startup or "Alembic not yet adopted" so it
instead accurately describes the system as it exists after Milestones 1–3:
Alembic-managed schema, an explicit `alembic upgrade head` step (never run
from app startup), and a documented procedure for both a fresh database and
an existing pre-Alembic one. This closes the spec's Technical Requirement
("update, not rewrite, the existing 'Migrations' sections") and its
Acceptance Criteria around documentation, and turns the Review gate's
non-blocking note — "the acceptance criterion about a new contributor
getting a working schema ... is descriptive rather than a hard pass/fail
check" — into a concrete, checkable step (Task 6).

## 2. Implementation Tasks

Each task is small and sequential; later tasks depend on earlier ones
within this list.

1. **Rewrite `README.md`'s "Migrations" section.**
   What: replace the section (currently: "creates tables on startup via
   `Base.metadata.create_all()` ... fine for local development ... the
   natural next step ... is to introduce Alembic") with one describing the
   adopted state: Alembic's file layout (`alembic.ini`, `alembic/env.py`,
   `alembic/versions/`), the two-migration history and what each creates,
   how to bring a fresh database up to date (`alembic upgrade head`), how
   to add a new migration (`alembic revision --autogenerate`, then hand-read
   the result against the model before committing — per the spec's
   "autogeneration drafts, it does not decide" rule), and the
   stamp-then-upgrade procedure for a database that already has `tasks`
   from before Alembic existed (`alembic stamp 2baa5d553906` then `alembic
   upgrade head`).
   Why: this is the spec's core doc-accuracy requirement — the section
   should describe Alembic as adopted, "covering both a fresh database and
   an existing pre-Alembic one" (spec Acceptance Criteria).
   Files: `README.md`.
   Depends on: nothing (first slice).

2. **Fix `README.md`'s "Running locally" and "Deploying" sections.**
   What: in "Running locally," insert an explicit step 5, `alembic upgrade
   head`, between `cp .env.example .env` and `uvicorn app.main:app
   --reload`, and remove the now-wrong "(creates tables on startup — see
   'Migrations' below)" parenthetical on the `uvicorn` step. In
   "Deploying," change "would add Alembic migrations (see above)" (phrased
   as a future step) to describe running `alembic upgrade head` as the
   existing, already-adopted release step.
   Why: Milestone 3 changed actual behavior — following the *current*
   README verbatim on a fresh checkout now fails with "relation does not
   exist" (verified in Milestone 3) until this step is documented.
   Files: `README.md`.
   Depends on: Task 1 (keeps both mentions of the same mechanism
   consistent).

3. **Rewrite `CLAUDE.md`'s "Migrations" section.**
   What: replace "**No Alembic yet** ... if Alembic is introduced, run
   `alembic upgrade head` as a release step" with the adopted-state
   description: Alembic is in use, migrations are append-only (no editing
   a merged migration — ship a correction as a new one), every
   autogenerated migration is hand-reviewed before commit, and `alembic
   upgrade head` runs as an explicit step, never from app startup (already
   true structurally after Milestone 3, now documented as such). Include
   the stamp-then-upgrade pointer for an existing pre-Alembic local
   database, consistent with `README.md`.
   Why: `CLAUDE.md` is what a future agent invocation reads first — leaving
   it describing a world that no longer exists (post Milestone 3) would
   actively mislead the next `/implement` or ad hoc change.
   Files: `CLAUDE.md`.
   Depends on: Task 1 (same content, keep the two docs consistent —
   `CLAUDE.md` should not contradict `README.md`).

4. **Fix the remaining stale `CLAUDE.md` spots that predate Milestones
   1–3.** What, each a one-line fix:
   - `## Commands` table's "Run locally" row: `docker compose up -d
     postgres` then `uvicorn app.main:app --reload` → insert `alembic
     upgrade head` between them, matching Task 2's README change.
   - `## Project Overview`'s parenthetical currently lists "auth,
     pagination, Alembic migrations" as deliberately deferred — remove
     "Alembic migrations" from that list (auth and pagination remain
     deferred; Alembic is not).
   - `## Project Layout`'s `db/ # engine/session, Base, init_db()` comment
     — `init_db()` no longer exists (Milestone 3); update to `# engine/session,
     Base`.
   - `## Testing` section's Integration-tests bullet currently says "`get_db`
     overridden to that same session, `init_db` no-op'd" — `init_db` no
     longer exists to no-op (Milestone 3 removed the monkeypatch entirely);
     update to describe the current fixture accurately.
   - `## Agent Do's and Don'ts`'s "Don't introduce Alembic or a new
     dependency/pattern without flagging it first" — Alembic already exists
     now, so keep the general "don't introduce a new dependency/pattern
     without flagging it first" rule but drop the now-inapplicable Alembic
     example, replacing it with the append-only-migration rule from Task 3
     (a schema change needs a matching, hand-reviewed migration, not a bare
     model edit).
   Why: these are the concrete instances of `CLAUDE.md` still describing
   pre-Milestone-3 reality found by grepping for `init_db`/`Alembic` across
   the repo; leaving any of them would contradict the rewritten Migrations
   section from Task 3.
   Files: `CLAUDE.md`.
   Depends on: Task 3.

5. **Add forward cross-references from the two specs this effort
   superseded.** What: this repo already has a precedent for this exact
   situation — `spec.md`'s own Scope section (line ~80) has a
   "**Update:** comments are no longer out of scope — see
   `.claude/specs/task-comments/spec.md`..." note added when a later spec
   superseded an earlier out-of-scope call. Follow that same convention
   here:
   - `spec.md`'s "Out of scope" bullet on "Schema migrations tooling
     (Alembic)" and its "Open Questions" entry asking "should the example
     add Alembic migrations instead of `create_all()`" — add a
     "**Update:**" line to each pointing at
     `.claude/specs/task-comments-migration/spec.md` as the follow-up spec
     that adopted Alembic.
   - `.claude/specs/task-comments/spec.md`'s "Out of Scope" bullet on
     "Alembic or any other migration tooling ... consistent with the root
     project's current deferral" — same "**Update:**" treatment.
   Do not rewrite the original historical prose in either document — these
   are historical records of decisions made at the time (per `CLAUDE.md`'s
   own framing: "see `spec.md` and `plan.md` for build history ... not
   oversights"); only a forward pointer is added, exactly as the existing
   precedent does.
   Why: this is the "root `spec.md` / `.claude/specs/task-comments/spec.md`
   cross-references" item the Milestone 2 plan explicitly named as deferred
   to this milestone.
   Files: `spec.md`, `.claude/specs/task-comments/spec.md`.
   Depends on: nothing (independent of Tasks 1–4).

6. **Verify the updated README against a scratch database.** What: from a
   throwaway Postgres database (never `docker-compose.yml`'s shared
   `postgres` service/volume — same discipline as every prior milestone),
   literally execute `README.md`'s rewritten "Running locally" steps in
   order — `docker compose`-equivalent Postgres startup, `.env` pointed at
   the scratch database, `alembic upgrade head`, then `uvicorn app.main:app`
   — and confirm one of the documented `curl` examples succeeds, with no
   hand-written SQL at any point.
   Why: turns the spec's Review-gate note (the "new contributor gets a
   working schema by following the docs" criterion is descriptive, not
   checkable, until the docs are actually written) into a concrete pass/
   fail check, now that Task 1–2 give it something real to execute.
   Files: none (verification only, against scratch infrastructure).
   Depends on: Tasks 1 and 2.

7. **Run the existing suite.** What: `pytest`, confirm all 51 tests still
   pass. Why: this milestone touches no application or test code, but
   `CLAUDE.md`'s own "Agent Do's and Don'ts" says to run it after any
   change regardless — a documentation-only milestone is not an exception.
   Files: none.
   Depends on: nothing, but run after Tasks 1–5 as a final check.

8. **Record the verification outcome.** What: once Tasks 1–7 pass, append
   a completion note to this plan (same style as Milestones 1–3's).
   Files: this plan file, appended to after implementation.
   Depends on: Tasks 1–7 all passing.

## 3. Documentation Strategy

**Update in place, don't rewrite history.** Two different kinds of
documents are touched here, and they get different treatment. `README.md`
and `CLAUDE.md` describe the system *as it is right now* — their
"Migrations" sections are simply wrong after Milestone 3 and get rewritten
to be correct, no different from fixing a bug. `spec.md` and
`.claude/specs/task-comments/spec.md`, by contrast, are dated records of
decisions made at specific points in time (`CLAUDE.md` itself says so) —
they get a forward-pointing "**Update:**" note, following the repo's own
existing precedent, not a rewrite of what was actually decided back then.

**Keep `README.md` and `CLAUDE.md` in agreement, not independently
accurate.** Both documents describe the same Migrations reality to two
different audiences (a human contributor vs. an agent reading `CLAUDE.md`
first). Task 3 deliberately depends on Task 1 so the same facts (file
layout, the two migrations, the transition procedure) are stated
consistently in both rather than drifting into two documents describing
the same thing slightly differently.

**One documentation change, not a staged rollout.** All of Tasks 1–5 land
in a single commit for this milestone, same principle as Milestone 3's
"one explicit cutover point" — there's no intermediate state where
`README.md` says Alembic is adopted but `CLAUDE.md` still says "no Alembic
yet," which would be actively confusing to whoever reads next.

## 4. Testing Strategy

- **No application or test code changes** — this milestone is
  documentation only, so there is no new automated coverage to add.
- **`pytest` (regression only):** run per `CLAUDE.md`'s own standing rule
  to run it after any change; expected to pass unchanged (51 tests) since
  nothing under `app/` or `tests/` is touched.
- **The real check is Task 6:** literally executing the rewritten
  "Running locally" README steps against a scratch Postgres database is
  what actually proves the documentation is correct, not just that it
  reads plausibly. This mirrors every prior milestone's standard of
  demonstrating behavior against a real database rather than asserting it
  from a read-through.
- The scratch database used for Task 6 is dropped afterward;
  `docker-compose.yml`'s shared `postgres` service/volume is never used as
  a stand-in for "a new contributor's fresh environment."

## 5. Acceptance Criteria

- [x] `README.md`'s "Migrations" section describes Alembic as adopted
      (file layout, the two-migration history, `alembic upgrade head`, how
      to author a new migration) and documents the stamp-then-upgrade
      transition for an existing pre-Alembic database — not just the fresh
      database case.
- [x] `README.md`'s "Running locally" section includes an explicit
      `alembic upgrade head` step in the correct order, and no longer
      claims the app "creates tables on startup."
- [x] `README.md`'s "Deploying" section describes `alembic upgrade head`
      as an already-adopted release step, not a future one.
- [x] `CLAUDE.md`'s "Migrations" section describes Alembic as adopted and
      does not contradict `README.md`'s version of the same facts.
- [x] `CLAUDE.md`'s "Commands" table, "Project Overview," "Project
      Layout," "Testing," and "Agent Do's and Don'ts" sections no longer
      reference `init_db()`, "no Alembic yet," or list Alembic as
      deliberately deferred scope.
- [x] `grep -rn "init_db" README.md CLAUDE.md` returns no results.
- [x] `spec.md`'s "Out of scope" Alembic bullet and its matching Open
      Question, and `.claude/specs/task-comments/spec.md`'s "Out of Scope"
      Alembic bullet, each carry a "**Update:**" cross-reference to
      `.claude/specs/task-comments-migration/spec.md`, following the
      existing precedent already in `spec.md` — with the original
      historical prose left intact.
- [x] Literally executing `README.md`'s rewritten "Running locally" steps
      against a scratch Postgres database (fresh checkout script assumed,
      `.env` pointed at the scratch DB) results in a working request/
      response (one of the documented `curl` examples succeeds) with zero
      hand-written SQL — confirmed by actually running the steps, not by
      inspection alone.
- [x] `pytest` (full existing suite, 51 tests) passes unchanged.

## 6. Risks and Assumptions

- **Drift between `README.md` and `CLAUDE.md` if only one is updated.**
  Mitigated by Task 3 explicitly depending on Task 1 and Task 6 checking
  both documents' claims against real behavior in the same pass, rather
  than trusting each document independently.
- **The `prompts/` directory (`prompts/database/generate-migration.md`,
  `prompts/database/optimize-query.md`, `prompts/documentation/create-runbook.md`,
  etc.) also describes "no Alembic yet" as a scenario/teaching example.**
  These are exercise prompt templates, not living project documentation,
  and were not named in the Milestone 2 plan's deferred-to-Milestone-4
  list (only `README.md`, `CLAUDE.md`, and the two spec cross-references
  were). Left untouched here as an explicitly out-of-scope, known gap —
  see Out of Scope — rather than silently ignored.
- **This milestone does not touch the root `plan.md`** (the original
  five-milestone app-build plan, fully checked off ✅), even though it
  also mentions `init_db()` in a historical, already-completed-milestone
  context (e.g. "router mounting, `init_db()` on startup"). Like `spec.md`,
  it's a historical record — but unlike `spec.md`'s Alembic bullet, the
  Milestone 2 plan never named `plan.md` as an out-of-scope item deferred
  here, so it's left alone rather than assumed into scope.
- **No CI check enforcing docs/code consistency going forward** — a future
  model or behavior change could reintroduce this exact kind of drift
  (spec's own Risks already name "no CI safety net yet" as a standing,
  unaddressed risk; unchanged by this milestone).

## 7. Out of Scope

- Any change to `app/`, `tests/`, or any other application/test code —
  this milestone is documentation only.
- Rewriting the historical prose of `spec.md`, `.claude/specs/task-comments/spec.md`,
  or the root `plan.md` — only forward-pointing "**Update:**" cross-references
  are added to the two named specs (Task 5); no historical claim is edited
  or removed.
- Updating `prompts/database/generate-migration.md`,
  `prompts/database/optimize-query.md`, `prompts/documentation/create-runbook.md`,
  or any other file under `prompts/` — these are exercise/teaching prompt
  templates, not living documentation, and were not named in scope for
  this milestone (see Risks).
- A CI check or other automated enforcement that documentation and code
  stay in sync going forward — not required by the spec, and consistent
  with its Non-goals around not building a general CI/tooling program.
- Any change to the migrations themselves, the application's startup
  behavior, or further verification of Milestones 1–3's already-proven
  behavior — this milestone assumes that work is done and correct, and
  only documents it.
