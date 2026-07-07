# Plan: Task Due-Date Reminders

Status: Approved
Traces to: [spec.md](./spec.md)
Last updated: 2026-07-07

## Decisions carried from the spec's Open Questions

The spec (§14) leaves four implementation-affecting questions to the plan.
All four are resolved here, not deferred further:

- **FR5: hard `422` vs. auto-clearing `remind_days_before` when `due_date`
  is removed.** This plan builds to the spec's own stated default:
  removing `due_date` while a reminder is configured, without also
  clearing the reminder in the same request, is a hard `422`. No
  auto-clear side effect is implemented. Reasoning: the spec explicitly
  frames auto-clear as the less-preferred alternative ("favors
  explicitness ... over convenience"), and NFR §6's "no side effect beyond
  persisting the value" reads more naturally as "no silent cross-field
  mutation" than as license to add one here.
- **Database-level `CHECK` constraint for `remind_days_before` → `due_date`,
  in addition to application-level enforcement.** Not built. The spec's own
  §15 Out of Scope already settles this ("the application-level enforcement
  in this spec is the floor, not necessarily the ceiling") — adding a `CHECK`
  constraint here would be building scope the spec explicitly deferred, not
  closing an open question left for the plan to decide either way.
- **Offset (`remind_days_before`) vs. absolute date (`remind_on`).** Offset,
  per the spec's own Data Model section (§8), which already commits to "one
  nullable integer" and gives its reasoning (stays correct automatically if
  `due_date` is later changed). This plan does not revisit that choice.
- **Upper bound on `remind_days_before`.** `Field(ge=0, le=3650)` (0 to 10
  years). Reasoning: no real due-date reminder needs more lead time than
  that, and an explicit cap follows the same pattern already used for
  `TaskCreate.title`/`description` (`max_length`, `app/schemas/task.py`) —
  bounding an extreme without constraining realistic use. 3650 is a schema
  detail, easy to change later without a migration since it isn't stored,
  only validated.

## Sequencing principle

Bottom-up dependency order — model/migration → repository passthrough →
service-layer validation → schema/API surface → documentation — matching
how `Task` and `Comment` were both built (`CLAUDE.md`'s layering). The one
deliberate departure from a purely mechanical bottom-up order: Milestone 2
(the FR2/FR5 cross-field invariant) gets exhaustive, DB-free unit-test
coverage of every transition *before* Milestone 3 wires it into the HTTP
surface. Spec §13 names this invariant as the single easiest thing to get
"half-right" (a naive per-field check would miss the "remove `due_date`,
reminder stays behind" case entirely) — proving it correct against a fast
unit suite first means a subtle bug there can't hide behind a passing
integration test that happens not to exercise the right transition.

## Milestone 1 — Data model, migration, and repository plumbing

Deliverables:
- `app/models/task.py`: `Task` gains `remind_days_before: Mapped[int |
  None] = mapped_column(Integer, nullable=True)` — no default, so every
  existing row reads back as `NULL` (spec §6 backward-compatibility
  requirement).
- `alembic revision --autogenerate -m "add remind_days_before to tasks"`,
  then hand-read the generated `upgrade()`/`downgrade()` against the model
  diff before committing (`CLAUDE.md`'s Migrations section) — expect a
  single `op.add_column('tasks', sa.Column('remind_days_before',
  sa.Integer(), nullable=True))` and its matching `op.drop_column` in
  `downgrade()`. No existing migration is edited.
- `app/repositories/tasks.py`: `create()` gains a `remind_days_before: int
  | None` keyword-only parameter, passed straight through to `Task(...)`.
  `update()` needs no change — it already applies arbitrary `**fields` via
  `setattr`.
- `tests/factories.py`: `make_task_payload()` and `make_task_model()` each
  gain an optional `remind_days_before` parameter (default `None`),
  following the existing parameter style — no hand-built payloads/models
  added elsewhere.

Acceptance criteria:
- New/extended integration test in `tests/integration/test_task_repository.py`:
  creating a `Task` via `TaskRepository.create(..., remind_days_before=N)`
  round-trips `N` on read-back; creating one without the argument (the
  existing call pattern, unchanged at every other call site) round-trips
  `None` — the concrete check behind spec §6/§12's backward-compatibility
  requirement.
- `alembic upgrade head` followed by `alembic downgrade -1` both run clean
  against a real, disposable Postgres instance (never `docker-compose.yml`'s
  shared `postgres` service/volume), matching the verification convention
  set by the two existing migrations.
- `pytest` passes.

Depends on: nothing (first slice).

**Status: Done (2026-07-07).** `app/models/task.py`'s `Task` gained
`remind_days_before: Mapped[int | None] = mapped_column(Integer,
nullable=True)`, no default. `app/repositories/tasks.py`'s `create()` gained
a `remind_days_before: int | None = None` keyword-only parameter passed
straight through to `Task(...)`; `update()` needed no change (already
generic `**fields`/`setattr`). `tests/factories.py` needed no edit: both
`make_task_payload()` and `make_task_model()` already accept arbitrary
`**overrides` (the same mechanism `due_date` already relies on — it isn't in
either function's defaults dict either), so `remind_days_before` is already
overridable with no code change; confirmed by using
`repository.create(..., remind_days_before=3)` directly in the new tests
below rather than needing a factory change. One deviation from the plan's
literal wording, documented rather than silently diverging.

Migration `4c68e39a12a3_add_remind_days_before_to_tasks.py` generated via
`alembic revision --autogenerate` against a scratch Postgres instance
already at head (baseline + comments), then hand-reviewed: a single
`op.add_column('tasks', sa.Column('remind_days_before', sa.Integer(),
nullable=True))` / matching `op.drop_column` pair, exactly as anticipated —
no edits needed. Verified end-to-end against a disposable
`postgres:16-alpine` container (`task-reminders-scratch-pg`, port 5599,
never `docker-compose.yml`'s shared `postgres` service/volume, removed
afterward): `alembic upgrade head` added the column (confirmed via `\d
tasks`), `alembic downgrade -1` cleanly removed it (confirmed via `\d
tasks` again), then re-upgraded to head before teardown.

Added `test_create_with_remind_days_before_round_trips` and
`test_create_without_remind_days_before_round_trips_as_none` to
`tests/integration/test_task_repository.py`. Full `pytest` suite green (53
passed, up from 51), with the only test-file diff being additive lines in
`test_task_repository.py` — zero pre-existing tests modified.

## Milestone 2 — Service-layer cross-field validation (FR2/FR5)

Deliverables:
- `app/core/exceptions.py`: `InvalidReminderConfigurationError(AppError)` —
  `code = "INVALID_REMINDER_CONFIGURATION"`, `status_code = 422`, message
  stating the resulting task would have a reminder with no `due_date` to be
  relative to. Mapped to a response automatically via the existing
  `to_error_response()` — no new branching added there.
- `app/services/tasks.py`:
  - `create()`: before delegating to the repository, if
    `payload.remind_days_before is not None and payload.due_date is None`,
    raise `InvalidReminderConfigurationError` (FR2). Otherwise pass
    `remind_days_before=payload.remind_days_before` through to
    `self._repository.create(...)` alongside the existing fields.
  - `update()`: after computing `fields = payload.model_dump(exclude_unset=True)`
    but before calling `self._repository.update(...)`, compute the task's
    *resulting* state — `effective_due_date = fields.get("due_date",
    task.due_date)` and `effective_remind_days_before =
    fields.get("remind_days_before", task.remind_days_before)` — and raise
    `InvalidReminderConfigurationError` if the former is `None` while the
    latter is not `None` (FR2/FR5, evaluated against resulting state, not
    just the fields present in this one request).
- `tests/unit/test_task_service.py`: extend with the transitions spec §10
  calls out by name — setting a reminder together with a `due_date`;
  rejecting a reminder with no `due_date` at create; clearing a reminder via
  explicit `remind_days_before: null`; rejecting a `due_date` removal that
  would leave a dangling reminder; allowing a `due_date` removal when the
  reminder is cleared in the same request; a `PATCH` that touches neither
  field is unaffected (regression check on the existing early-return for
  no-op updates).

Acceptance criteria:
- All six transitions above are asserted as distinct unit tests against
  `FakeTaskRepository` — no real database or FastAPI app involved at this
  tier (`CLAUDE.md`'s Testing section).
- Each rejection asserts the exception raised is specifically
  `InvalidReminderConfigurationError`, not a bare `ValueError` or the
  existing `NotFoundError`.
- `pytest` passes.

Depends on: Milestone 1.

**Status: Done (2026-07-07).** `app/core/exceptions.py` gained
`InvalidReminderConfigurationError(AppError)` — `code =
"INVALID_REMINDER_CONFIGURATION"`, `status_code = 422` — mapped
automatically through the existing `to_error_response()`, no new branching
added there. `app/services/tasks.py`'s `create()` now raises it when
`payload.remind_days_before is not None and payload.due_date is None`
(FR2), otherwise forwards `remind_days_before` to the repository; `update()`
now computes `effective_due_date`/`effective_remind_days_before` by merging
`fields` (the explicitly-sent keys) onto the current task's values, and
raises the same error if the resulting state has a reminder but no
`due_date` (FR2/FR5) — evaluated, and raising, *before* any repository call,
so a rejected request never partially applies.

**One necessary deviation from the plan's literal wording:** the plan's
Milestone 2 service code references `payload.remind_days_before`, which
requires `TaskCreate`/`TaskUpdate` to already expose that attribute —
but the schema field is Milestone 3's stated deliverable, not Milestone 2's.
Without it, Pydantic v2's default `extra="ignore"` behavior means
constructing `TaskCreate(remind_days_before=3, ...)` would silently drop the
value rather than error, and `payload.remind_days_before` would raise
`AttributeError` — making the plan's own service logic inoperable and the
required unit tests impossible to write. Resolved by adding a bare
`remind_days_before: int | None = None` attribute (no `Field` constraints,
no description) to both `TaskCreate` and `TaskUpdate` in `app/schemas/task.py`
now, with a comment marking it as Milestone 2 scaffolding. Milestone 3 still
owns the full job: `Field(ge=0, le=3650, description=...)`, the `TaskRead`
exposure, and the API-level tests — nothing here anticipates that work.
`TaskRead`/`TaskList` were **not** touched, so the field still doesn't
appear in any API response yet.

A second, pre-existing `FakeTaskRepository` in `tests/unit/test_comment_service.py`
(used only for `CommentService`'s tests) also needed its `create()` signature
extended with `remind_days_before=None`, for the same reason
`tests/unit/test_task_service.py`'s fake did in Milestone 1's carryover —
`TaskService.create()` now unconditionally forwards that keyword to
whatever repository it's given, so every fake implementing the interface
must accept it. This is a one-line interface-parity fix on a file outside
the plan's named Milestone 2 file list, not a scope expansion — without it
the pre-existing comment-service suite would regress.

Added six unit tests to `tests/unit/test_task_service.py` covering all
transitions named in spec §10: create with reminder + due_date (succeeds);
create with reminder, no due_date (raises, asserts `code`/`status_code`);
clearing a reminder via explicit `null`; removing `due_date` with an
existing reminder, unchanged (raises, and asserts the task's stored state
is untouched — no partial apply); removing `due_date` and clearing the
reminder together (succeeds); and a regression test patching an unrelated
field (`title`) on a task that already has a valid due_date+reminder pair,
proving the resulting-state merge itself doesn't spuriously reject a
same-state carry-forward (the existing no-op test only exercised the
early-return path, not this merge logic). Full `pytest` suite green (59
passed, up from 53) — the only test-file diffs are additive lines in
`test_task_service.py` plus the one-line interface fix in
`test_comment_service.py` described above.

## Milestone 3 — Schemas and API contract

Deliverables:
- `app/schemas/task.py`: `TaskCreate`, `TaskUpdate`, and `TaskRead` each
  gain `remind_days_before: int | None = Field(default=None, ge=0,
  le=3650, description=...)`. The `description` states plainly that setting
  this field does not cause any notification to be sent (spec §11/§13's
  single most important line) — visible directly in `/docs` without a
  separate hand-written doc.
- `FakeTaskRepository` (wherever `tests/unit/test_task_service.py` defines
  it) and `TaskRepository.update()`'s already-generic `**fields` require no
  further change — confirmed, not re-implemented, in this milestone.
- `tests/integration/test_tasks_api.py`: extend with
  - `POST /v1/tasks` with both `due_date` and `remind_days_before` → `201`,
    both fields populated in the response (spec §12).
  - `POST /v1/tasks` with `remind_days_before` but no `due_date` → `422`
    with the standard error envelope, `code ==
    "INVALID_REMINDER_CONFIGURATION"`.
  - `PATCH /v1/tasks/{id}`: set a reminder on a task that already has a
    `due_date`; read it back via `GET`; clear it via
    `remind_days_before: null`; each asserted as its own transition.
  - `PATCH /v1/tasks/{id}` removing `due_date` from a task with an existing
    reminder, without clearing the reminder → `422`, same error code.
  - `PATCH /v1/tasks/{id}` removing `due_date` *and* clearing
    `remind_days_before` in the same request → `200`.
  - `GET /v1/tasks` and `GET /v1/tasks/{id}` include `remind_days_before`
    (`null` when unset) for a task seeded directly via
    `make_task_model()` without the field, proving pre-existing/unrelated
    tasks aren't affected.

Acceptance criteria:
- All bullets above pass as automated tests; spec §12's checklist items
  covering the API contract are fully satisfied by this milestone.
- Manual check: `/docs` shows `remind_days_before` on
  `TaskCreate`/`TaskUpdate`/`TaskRead` with the "does not send anything"
  description visible.
- No new endpoint, router, or top-level route exists — confirmed by
  inspection of `app/api/v1/routers/tasks.py` (unchanged) and
  `app/api/v1/__init__.py` (unchanged).
- `pytest` passes.

Depends on: Milestone 2.

**Status: Done (2026-07-07).** `app/schemas/task.py`: `TaskCreate.remind_days_before`
and `TaskUpdate.remind_days_before` upgraded from Milestone 2's bare scaffolding
attribute to `Field(default=None, ge=0, le=3650, description=...)`, the description
stating plainly that configuring this does not send any notification (spec
§11/§13). `TaskRead` gained `remind_days_before: int | None = Field(description=...)`
— a new field with its own reminder-specific description text (`null` meaning "no
reminder configured"), so it now appears in every `Task` representation returned by
`POST`/`GET`/`PATCH`. `FakeTaskRepository` and `TaskRepository.update()` needed no
change, as anticipated.

`tests/integration/test_tasks_api.py` gained seven tests: create with
`due_date`+`remind_days_before` → `201` with both fields populated; create with
`remind_days_before` but no `due_date` → `422` / `INVALID_REMINDER_CONFIGURATION`;
a `PATCH` sequence setting, reading back (via `GET`), then clearing a reminder;
`PATCH` removing `due_date` with an existing reminder → `422`, same code; `PATCH`
removing `due_date` *and* clearing the reminder together → `200`; and `GET`
(list and single) returning `remind_days_before: null` for a task seeded directly
via `make_task_model()` (bypassing the API), proving pre-existing/unrelated tasks
are unaffected. `tests/factories.py` needed no change — `make_task_model()`'s
existing `**overrides` mechanism already accepts `remind_days_before` (same as
Milestone 1's finding for `make_task_payload()`/`make_task_model()` generally).

**One necessary deviation from the plan's literal wording:** the plan's deliverable
list only mentions `TaskCreate`/`TaskUpdate`/`TaskRead` gaining the field with a
single shared `description=...`, without calling out that `TaskRead`'s prior bare
declaration (added, per spec, with no `Field` at all — see `due_date`/`status`/
`priority` in the same class) needed its own `Field(description=...)` distinct from
`TaskCreate`/`TaskUpdate`'s (phrased for a request body, not a response). Read
literally, "TaskRead gains `remind_days_before` in the response body" doesn't by
itself require a description on that specific field — but spec §11 explicitly
requires the caveat on all three schemas, so a `TaskRead` without one would leave
`/docs` silently inconsistent for exactly the field spec §13 calls the single
biggest risk to get right. Resolved by giving `TaskRead` its own
`Field(description=...)` (no `default=`/`ge`/`le`, since it's a response field
populated from the ORM row, not a validated request field) with response-appropriate
wording. Confirmed via `app.openapi()` that all three schemas now carry a
non-empty `description` for this field.

A second, forced, one-line deviation: `TaskRead`'s existing
`test_response_does_not_leak_unexpected_fields` integration test asserts an exact
`set(created.keys())` — adding `remind_days_before` to `TaskRead`'s response
necessarily changes that set, so the test's expected key set was updated to include
it. This is a required consequence of the milestone's own deliverable (`TaskRead`
gaining a field), not an unrelated test change, but is called out here since the
plan's Milestone 4 acceptance criteria treat "zero pre-existing tests modified
outside Milestones 1–3's file list" as a integrity signal — this edit is inside
that file list (`test_tasks_api.py`) and is the one pre-existing assertion this
milestone's schema change could not avoid touching.

Full `pytest` suite green (65 passed, up from 59). Manually verified against a
disposable `postgres:16-alpine` scratch container (`task-reminders-m3-scratch`,
port 5598, never `docker-compose.yml`'s shared `postgres` service/volume, removed
afterward — the shared service was briefly stopped/restarted around this check):
`alembic upgrade head` applied cleanly through `4c68e39a12a3` (Milestone 1's
migration), then a live `uvicorn` process was driven with real HTTP requests —
`POST` with `due_date`+`remind_days_before` → `201` with both fields; `POST` with
`remind_days_before` alone → `422`/`INVALID_REMINDER_CONFIGURATION`; `PATCH`
removing `due_date` with a reminder still set → `422`, same code; `PATCH` removing
both together → `200`; `GET` (list and single) reflecting the field. `/openapi.json`
confirmed a non-empty `description` on `remind_days_before` in all three schemas,
and `GET /docs` returned `200`. No new route/router/endpoint exists — confirmed by
`app/api/v1/routers/tasks.py` and `app/api/v1/__init__.py` being untouched by this
milestone's diff.

## Milestone 4 — Documentation

Deliverables:
- Root `README.md`'s `Task` field/schema documentation: add
  `remind_days_before`, explicitly noting it does not cause any
  notification to be sent (spec §11) — the same caveat as the schema
  docstring from Milestone 3, stated in the human-facing doc too.

Acceptance criteria:
- `README.md`'s `Task` field table/section lists `remind_days_before` with
  the "no notification is sent" caveat, read through manually once after
  editing (spec §11's own acceptance bar: "confirmed by a manual
  read-through").
- Full `pytest` suite green, with **zero** pre-existing tests modified —
  a diff to any test file that isn't `test_task_repository.py`,
  `test_task_service.py`, `test_tasks_api.py`, or `factories.py` (all
  touched only additively by Milestones 1–3) is a signal something leaked
  outside this feature's scope (spec §12).

Depends on: Milestone 3.

**Status: Done (2026-07-07).** Root `README.md` gained a new "Task fields"
section (there was no pre-existing `Task` field/schema documentation section
to extend — this milestone's own deliverable, read literally, presumes one
exists; see deviation note below), placed after the `curl` walkthrough in
"Running locally". It documents all seven `Task` fields
(`id`/`title`/`description`/`status`/`priority`/`due_date`/`created_at`/
`updated_at`, plus the new `remind_days_before`) in a table, so the new
field's entry (its `0`–`3650` bound, that it requires `due_date` in the same
request or already present, the `422`/`INVALID_REMINDER_CONFIGURATION`
failure mode, and — bolded, matching spec §13's "single biggest risk"
framing — that configuring it persists a preference only and sends no
notification of any kind) reads in context rather than as an orphaned
one-row table.

**One necessary deviation from the plan's literal wording:** the plan's
Milestone 4 deliverable says README's "`Task` field/schema documentation"
should "gain `remind_days_before`" — phrasing that presumes such a section
already exists to be extended. It doesn't; `README.md` before this milestone
had no field-by-field `Task` documentation at all (confirmed by grep — the
only prior mention of `due_date`/`priority` was inline in one `curl`
example). Adding only a single-row table for `remind_days_before` in
isolation would have been more misleading than helpful (a reader would
reasonably wonder why only one of `Task`'s eight fields is documented).
Resolved by writing the full field table spec §11 implicitly requires
context for, sourced directly from `app/schemas/task.py`/`app/models/task.py`
(verified against both, including exact enum values for `status`/`priority`
and that `status` isn't settable on `TaskCreate`) — not a re-derivation from
memory. This is judged to be in scope for "documentation identified by the
plan" (the deliverable names this exact README section) rather than
"unrelated improvement," since the section couldn't otherwise contain the
required entry in a coherent form.

Manual read-through performed (spec §11/§12's own acceptance bar) — the
table renders correctly (pipes inside cells escaped as `\|`), the
notification-caveat line is bolded and unambiguous, and cross-checked word
values (`status`/`priority` enum members, `remind_days_before`'s bounds and
422 error code) against `app/models/task.py`/`app/schemas/task.py`/
`app/core/exceptions.py` directly rather than trusting Milestone 3's prose.
No contradiction found between this section and the OpenAPI schema
descriptions from Milestone 3.

Full `pytest` suite green (65 passed — unchanged from Milestone 3, as
expected for a documentation-only change). `git status`/`git diff --stat`
confirm the only change in this milestone's diff is `README.md`; zero test
files were touched, satisfying this milestone's own "zero pre-existing
tests modified" acceptance criterion trivially (no test files were touched
at all, not just none of the four named ones).

## Review gates

Review happens after every milestone, each landed as its own commit (or
short PR). "Review" means: `pytest` passes in full, and for Milestones 1, 3,
and 4 specifically, the change is exercised for real — Milestone 1's
migration against a disposable Postgres instance, Milestone 3's endpoints
against a running app (`/docs` or a manual `curl`/`httpx` call, not just the
test suite), Milestone 4's README read through by hand — matching this
repo's `verify` skill expectation that a runtime surface gets driven, not
only asserted by tests. No milestone starts before the previous one's tests
are green.

## Out of scope for this plan

Nothing in the spec's Scope (§3) or Functional Requirements (§5) is
deferred — Milestones 1–4 cover FR1–FR6, the API contract in §7, the data
model in §8, the error handling in §9, and the documentation requirements
in §11 in full. Everything in the spec's own §15 Out of Scope (notification
delivery of any kind, a scheduler/background process, a "reminders due
soon" endpoint or filter, multiple reminders per task, any change to
`due_date`'s type/precision, recipient/identity, recurring reminders, and a
database-level `CHECK` constraint) remains out of scope for this plan too,
unchanged — this plan builds exactly the configuration surface the spec
defines, no delivery mechanism and no defense-in-depth beyond it.

---

## Review gate

Approved: implementation strategy and milestone sequencing are consistent
with the approved spec, preserve the Router → Service → Repository → Model
layering, and resolve all four Open Questions (§14 of the spec) as
documented above. Proceed with implementation per Milestones 1–4.

Approved by: Nayan155 (via Claude Code plan review)
Date: 2026-07-07
