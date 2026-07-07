# Spec: Task Due-Date Reminders

Status: Approved
Owner: Engineering (SmartSense)
Last updated: 2026-07-07

*Scope note: `Task.due_date` already exists and is already exposed through
the API (`app/models/task.py`, `app/schemas/task.py`). This spec covers
adding an **optional reminder configuration** on top of that existing
field — a client can say "remind me N days before this task is due." It
covers persisting and returning that configuration through the API only.
It does **not** cover actually sending a notification of any kind — see
Non-goals and Out of Scope.*

## 1. Background

`Task` already carries `due_date` (a nullable, date-only field — no
time-of-day) via `TaskCreate`, `TaskUpdate`, and `TaskRead`
(`app/schemas/task.py`). There is currently no way for a client to ask the
API to do anything with that date beyond storing and returning it. The
Task Tracker API otherwise has no authentication, no user/identity
concept, no email or push notification service, and no background
job/scheduler process (`CLAUDE.md`'s Security section; `app/main.py`'s
lifespan only manages the DB engine). Any of those would be new
infrastructure, not an extension of the existing CRUD surface.

## 2. Problem Statement

A client that wants to be reminded a task is coming due today has to poll
`GET /v1/tasks` (or `GET /v1/tasks/{id}`) and compare `due_date` against
the current date itself — the API has no concept of "this task wants a
reminder" at all. There is nowhere to record *that* a reminder was wanted,
let alone *when* relative to the due date. This spec adds that
configuration to the API surface, without attempting to solve delivery
(see Non-goals).

## 3. Goals

- Let a client optionally configure a single reminder on a task, expressed
  as a whole number of days before `due_date`.
- Let a client read back a task's current reminder configuration through
  the same representation already used for every other `Task` field.
- Let a client clear a previously configured reminder.
- Guarantee a reminder can never exist on a task without a `due_date` to
  be relative to — a data-integrity rule enforced at the API boundary, not
  just documented.
- Do all of this as an extension of the existing `Task` resource and its
  existing endpoints — no new resource, no new router.

## 4. Non-goals

- **Not building notification delivery.** No email, push, SMS, webhook, or
  any other outbound notification is sent by this spec. "Configuring a
  reminder" only means persisting the client's request; nothing reads
  that configuration and acts on it yet. Building that is a separate,
  future effort once this project has the infrastructure it requires
  (identity/recipient, a delivery channel, a scheduler) — see Out of
  Scope.
- **Not a scheduler or background worker.** No new process is introduced
  to periodically check which reminders are "due" — that's part of
  delivery, not configuration.
- **Not multiple reminders per task.** A task carries at most one reminder
  configuration. Needing several reminders on one task (e.g. "1 day
  before" *and* "1 hour before") is a larger feature, deliberately not
  built here.
- **Not a change to `due_date`'s type or precision.** `due_date` stays a
  date with no time-of-day; a reminder is expressed in whole days, not
  hours or minutes, consistent with that existing precision.
- **Not adding identity/authentication.** There is still no concept of
  "who" gets reminded — consistent with the rest of this API's documented
  no-auth stance (`CLAUDE.md`'s Security section).

## 5. Functional Requirements

- FR1: A client can set a reminder on a task by supplying
  `remind_days_before` (a non-negative whole number of days) together
  with, or on top of, a `due_date` — at creation (`POST /v1/tasks`) or via
  update (`PATCH /v1/tasks/{id}`).
- FR2: `remind_days_before` can only be set on a task that has a
  `due_date` — as a result of the same request, if not already stored.
  A request that would leave a task with `remind_days_before` set but
  `due_date` absent fails validation (see Error Handling); the server
  never silently drops one field to satisfy the other.
- FR3: A client can read a task's current reminder configuration as part
  of the standard `Task` representation returned by every existing
  read/write endpoint (`POST`, `GET` (list and single), `PATCH`) — no
  separate endpoint is needed to see it.
- FR4: A client can clear a previously configured reminder by explicitly
  sending `remind_days_before: null` in a `PATCH` request, independent of
  `due_date` — consistent with how any other nullable `Task` field is
  already cleared via the existing "only explicitly-sent fields are
  applied" update semantics.
- FR5: A `PATCH` that removes `due_date` (sets it to `null`) from a task
  that currently has a reminder configured fails validation *unless* the
  same request also clears `remind_days_before` — this is the concrete
  instance of FR2's invariant applied to updates, since it must hold
  against the task's *resulting* state, not just the fields present in a
  single request in isolation. (Flagged as a default decision, not a
  closed one — see Open Questions.)
- FR6: Setting or clearing `remind_days_before` has no side effect beyond
  persisting the value — no notification is sent, queued, or scheduled
  (Non-goals).

## 6. Non-functional Requirements

- **Consistency of architecture.** This is a field-level extension of the
  existing `Task` schemas/model/repository/service — no new layer, no new
  router, no shortcut around the existing routers → services →
  repositories → models layering.
- **Consistency of contract.** The new validation failure (FR2/FR5) uses
  the same standard error envelope and centralized exception-to-response
  mapping already in place (`app/core/exceptions.py`) — not a new,
  parallel error-handling path.
- **No new operational surface.** No new config, external dependency, or
  background process — this is a new nullable column and some validation
  logic, served by the same app process and database as everything else.
- **Backward compatibility.** Every existing task (all of which currently
  have no reminder) must read back with `remind_days_before: null` — the
  new column is nullable with no default value that would imply a
  reminder was requested.

## 7. API Requirements

No new endpoints or routes. The existing `Task` endpoints are extended:

- `POST /v1/tasks` — `TaskCreate` gains an optional `remind_days_before`.
  Fails per FR2 if supplied without a `due_date` in the same request.
- `PATCH /v1/tasks/{id}` — `TaskUpdate` gains an optional, nullable
  `remind_days_before`, following the existing "only fields explicitly
  sent are applied" semantics. Fails per FR2/FR5 if the request would
  leave the task with a reminder but no `due_date`.
- `GET /v1/tasks` / `GET /v1/tasks/{id}` — `TaskRead` (and therefore
  `TaskList`) gains `remind_days_before` in the response body, `null`
  when no reminder is configured.
- `DELETE /v1/tasks/{id}` — unchanged; deleting a task removes its
  reminder configuration along with everything else about it (no separate
  cleanup needed, since it's a plain column, not a related row).

### Response contracts

High-level only — exact schema field types/constraints are a plan/
implementation detail, not fixed here.

| Endpoint | Status | Response model |
|---|---|---|
| `POST /v1/tasks` | `201 Created` | `TaskRead`, including `remind_days_before` (`null` if not supplied). |
| `POST /v1/tasks` | `422 Unprocessable Entity` | Standard error envelope — `remind_days_before` supplied without a `due_date` (FR2), or an existing field-level failure (e.g. blank `title`), unchanged from today. |
| `PATCH /v1/tasks/{id}` | `200 OK` | `TaskRead`, reflecting the updated reminder configuration. |
| `PATCH /v1/tasks/{id}` | `422 Unprocessable Entity` | Standard error envelope — the resulting task would have `remind_days_before` set but no `due_date` (FR2/FR5), or an existing field-level failure. |
| `PATCH /v1/tasks/{id}` | `404 Not Found` | Standard error envelope — task `{id}` doesn't exist (unchanged from today). |
| `GET /v1/tasks`, `GET /v1/tasks/{id}` | `200 OK` | `TaskList` / `TaskRead`, both including `remind_days_before` (unchanged status codes from today). |

## 8. Data Model

- `Task` gains one new column: `remind_days_before`, a nullable
  non-negative integer. `null` means "no reminder configured" — there is
  no separate boolean flag, so there is no representable state where a
  flag and a value disagree.
- The invariant "`remind_days_before` set implies `due_date` set" (FR2) is
  enforced at the application/service boundary, the same place `Task`'s
  other cross-field rules would be enforced — it is not (in this spec)
  additionally enforced as a database-level `CHECK` constraint. Whether it
  should be is an Open Question for the plan.
- This is an additive schema change: a new nullable column with no
  default that implies a reminder. Per `CLAUDE.md`'s Migrations section,
  it requires a new, hand-reviewed Alembic migration (`alembic revision
  --autogenerate` against the current head) — no existing migration is
  edited.
- No new table, no new foreign key, no change to `due_date`'s column type.

**Extensibility.** This spec deliberately stores the smallest viable
shape (one nullable integer). A future delivery-mechanism spec building
on this should be able to add its own fields/table (e.g. a delivery
channel, a "last reminded at" timestamp, support for multiple reminders)
without changing the meaning of `remind_days_before` or breaking the
contracts above. No such extension is built now.

## 9. Error Handling

- Field-level failures (missing/blank `title`, a non-integer or negative
  `remind_days_before`, etc.) are boundary validation handled the same way
  every other `Task` field already is, via the Pydantic schema layer —
  no hand-checking in the service.
- The cross-field rule in FR2/FR5 cannot be fully expressed as a
  single-schema field constraint for `PATCH` (a partial update must be
  validated against the task's *resulting* state, not just the fields
  present in that one request) — it requires a new, small domain
  validation step in the service layer, surfaced as a new `AppError`
  subclass (e.g. `InvalidReminderConfigurationError`) mapped to `422`
  through the existing centralized `to_error_response()` mapping
  (`app/core/exceptions.py`) — not a new, ad hoc error-handling path.
- This is one new error code, justified by FR2/FR5 being a genuine
  cross-field business rule that doesn't fit Pydantic's per-field
  validation model. No other new error codes are anticipated.

## 10. Testing Requirements

- **Unit tests**: `TaskService` (or wherever FR2/FR5's cross-field check
  lives) covering: setting a reminder together with a `due_date`;
  rejecting a reminder with no `due_date`; clearing a reminder via
  explicit `null`; rejecting a `due_date` removal that would leave a
  dangling reminder; allowing a `due_date` removal when the reminder is
  cleared in the same request.
- **Integration tests**:
  - `TaskRepository`/DB round-trip: `remind_days_before` persists and
    reads back correctly, and existing rows (no migration data backfill)
    read back as `null`.
  - Full app via `TestClient`: `POST`/`PATCH` happy paths returning the
    new field; the `422` path for FR2 (create) and FR5 (update); `GET`
    (list and single) returning the field for tasks with and without a
    reminder configured.
- Test data: extend `tests/factories.py`'s existing task payload/model
  factories with an optional `remind_days_before` parameter, rather than
  hand-building payloads inline.

## 11. Documentation Requirements

- Root `README.md`'s `Task` field/schema documentation gains
  `remind_days_before`, explicitly noting that configuring it does not
  cause any notification to be sent (see Risks — this is the single most
  important line to get right, to avoid a client assuming delivery
  exists).
- The `TaskCreate`/`TaskUpdate`/`TaskRead` schema field itself carries a
  docstring/description saying the same thing, so it's visible directly
  in `/docs` (OpenAPI) without a separate hand-written doc.

## 12. Success Criteria

Each item below is written to be checked off individually during
implementation review.

- `pytest` passes, including the new unit/integration tests from Section
  10, with zero pre-existing tests broken or modified to accommodate this
  change.
- `POST /v1/tasks` with both `due_date` and `remind_days_before` returns
  `201` with both fields correctly populated in the response.
- `POST /v1/tasks` with `remind_days_before` but no `due_date` returns
  `422` with the standard error envelope — verified by an automated test.
- `PATCH /v1/tasks/{id}` can set, read back, and clear
  (`remind_days_before: null`) a reminder on a task that already has a
  `due_date` — verified by automated tests for each transition.
- `PATCH /v1/tasks/{id}` that removes `due_date` from a task with an
  existing reminder, without also clearing the reminder, returns `422`
  with the standard error envelope — verified by an automated test.
- `PATCH /v1/tasks/{id}` that removes `due_date` *and* clears
  `remind_days_before` in the same request succeeds (`200`) — verified by
  an automated test.
- `GET /v1/tasks` and `GET /v1/tasks/{id}` include `remind_days_before`
  (`null` when unset) for every task, including tasks created before this
  change — verified by an automated test seeding a task without the
  field.
- A new, hand-reviewed Alembic migration exists for the new column,
  verified against a real Postgres database per the existing migration
  verification convention (`CLAUDE.md`'s Migrations section).
- No new endpoint, router, or top-level route exists — a code review
  confirms this is a pure extension of the existing `Task`
  schemas/model/service/repository.
- `README.md` and `/docs` (OpenAPI) reflect the new field, including the
  "this does not send anything" caveat — confirmed by a manual
  read-through after implementation.

## 13. Risks

- **Misleading affordance.** The single biggest risk of this spec: a
  client sees `remind_days_before` on `Task` and reasonably assumes
  setting it *does something* — that a notification will actually arrive.
  Nothing will, until a future delivery mechanism is built. This must be
  explicit and hard to miss in both the schema field description and
  `README.md` (Documentation Requirements), or this feature actively
  misleads its own consumers.
- **Cross-field validation is easy to get half-right.** FR2/FR5's
  invariant must hold against the task's *resulting* state after a
  partial `PATCH`, not just the literal fields present in the request
  body — a naive per-field check would miss the "remove `due_date`,
  reminder stays behind" case (FR5) entirely.
- **Date-only ambiguity compounds here.** `due_date` already has no
  timezone/time-of-day, which is a pre-existing, accepted ambiguity for a
  plain due date. Once a real reminder *delivery* mechanism eventually
  reads `remind_days_before`, "N days before, in which timezone, at what
  time of day" becomes a real question — not solved here, but this spec
  is what a future delivery spec will have to build on top of.
- **Naming becomes a contract.** Whatever this spec names the field and
  its error code, a future delivery-mechanism spec inherits — worth
  getting reviewer sign-off on the name specifically (see Open
  Questions), not just the behavior.

## 14. Open Questions

- Should removing `due_date` while a reminder is configured be a hard
  `422` validation failure (this spec's default, FR5), or should the
  server instead auto-clear `remind_days_before` as a side effect of
  removing `due_date`? The default here favors explicitness (no silent
  cross-field mutation) over convenience. (Owner: plan reviewer — needs a
  decision before the plan is written.)
- Should the invariant that `remind_days_before` requires a `due_date` be
  enforced only at the application layer (this spec's default), or also as
  a database-level `CHECK` constraint for defense-in-depth? (Owner: plan
  author — mirrors the same question already open for `task_status`/
  `task_priority` per the migration implementation review.)
- Is `remind_days_before` (an offset in days) the right shape, or would a
  future delivery mechanism be better served by storing an absolute
  `remind_on` date computed at write time? Both are derivable from each
  other today since `due_date` is required for either to make sense;
  this spec picks the offset form because it stays correct automatically
  if `due_date` is later changed. (Owner: plan author — confirm before
  implementation, since it's harder to change post-migration.)
- What upper bound, if any, should `remind_days_before` have? (Owner:
  plan author — a schema-level detail, not fixed here.)

## 15. Out of Scope

- Actually sending a reminder notification of any kind (email, push, SMS,
  webhook, in-app) — see Non-goals.
- Any background/scheduled process that checks which reminders are due.
- Any endpoint or query filter for "tasks with a reminder due soon" (e.g.
  extending `GET /v1/tasks`'s existing status filter) — deferred to
  whichever future spec builds delivery, since it only becomes useful
  once something consumes it.
- Multiple reminders per task.
- Any change to `due_date`'s type, precision, or existing validation.
- Recipient/identity for a reminder (who gets notified) — this API has no
  auth or user accounts to attribute a reminder to (see Non-goals).
- Recurring or repeating reminders.
- A database-level `CHECK` constraint for the `remind_days_before` →
  `due_date` invariant (see Open Questions) — the application-level
  enforcement in this spec is the floor, not necessarily the ceiling.

---

## Review gate

*This spec needs explicit human sign-off before planning starts against
it.*

Approved by: Nayan155
Date: 2026-07-07
