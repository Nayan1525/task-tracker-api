# Spec: Task Comments

Status: Approved
Owner: Engineering (SmartSense)
Last updated: 2026-07-06

*Scope note: this spec covers discrete, user-authored **comments** on a
task only. A general activity/audit timeline (automatic entries for status
changes, field edits, etc.) is explicitly **not** built here — see
Non-goals and Out of Scope.*

## 1. Background

The Task Tracker API (`spec.md` at the repo root) currently exposes a single
resource, `Task`, with no child resources. `CLAUDE.md` and the root spec
both list "sub-resources such as comments" as explicitly out of scope for
the original build. This spec proposes bringing that sub-resource in, using
the same layered architecture (routers → services → repositories → models),
error envelope, and testing conventions already established for `Task`.

## 2. Problem Statement

A `Task` today only carries its own fields (`title`, `description`,
`status`, `priority`, `due_date`). There is no way for a user or system
consuming the API to leave a note on a task, ask a question about it, or
record context that isn't a structured field — and no way to retrieve that
history later. Any such discussion currently has to happen outside the API
entirely (chat, email), disconnected from the task it concerns.

## 3. Goals

- Let a client attach a comment to a specific, existing task.
- Let a client retrieve the full set of comments belonging to a task.
- Preserve comments as an immutable record: once created, a comment's
  content never changes through the API.
- Guarantee referential integrity: a comment can never exist detached from
  a task, and removing a task removes its comments with it.
- Fit the new resource into the existing layering, error-handling, and
  testing conventions without deviation.

## 4. Non-goals

- **Not a general activity/audit log.** Automatic system-generated entries
  (e.g. "status changed from `todo` to `in_progress`", "priority changed")
  are a different, larger feature — recording every field mutation is a
  separate concern from user-authored comments and is not attempted here.
- **Not a discussion/collaboration feature.** No threading, replies,
  reactions, @mentions, or notifications — a comment is a flat, single
  entry with no relationship to other comments beyond sharing a `task_id`.
- **Not an editing or moderation feature.** No update or delete of an
  individual comment, and no admin override, by design (see Functional
  Requirements).
- **Not an identity feature.** This spec does not introduce user accounts
  or authentication to attribute comments reliably — `author` is a
  free-text field, consistent with the rest of the API being unauthenticated
  (see Risks).

## 5. Functional Requirements

- FR1: A client can create a comment on an existing task, supplying an
  `author` and a `message`. The server assigns `id`, `task_id`, and
  `created_at`.
- FR2: Creating a comment against a `task_id` that does not exist fails —
  it must not silently create an orphaned comment.
- FR3: A client can retrieve the comments belonging to a given task.
- FR4: Comments returned for a task are ordered chronologically, oldest
  first (creation order ascending) — a natural timeline reading order,
  top to bottom. This is a fixed, documented contract, not an
  implementation-dependent default.
- FR5: A comment cannot exist without a valid, existing owning task —
  enforced as a standing data-integrity constraint, not just at
  creation time.
- FR6: Deleting a task (the existing `DELETE /v1/tasks/{id}`) also removes
  every comment that belongs to it, as an atomic side effect of that same
  operation — no orphaned comments survive a task deletion.
- FR7: There is no endpoint, in this spec, that updates or deletes a single
  comment. A comment's `author`, `message`, and `created_at` are fixed for
  its lifetime.
- FR8: `author` and `message` are both required and non-empty; both are
  validated at the API boundary (bounded length, non-blank) consistent with
  how `Task.title`/`description` are already validated — exact limits are
  a schema-level detail for the plan/implementation, not fixed here.

## 6. Non-functional Requirements

- **Consistency of architecture.** The new resource follows the same
  routers → services → repositories → models layering as `Task`; no
  shortcut that collapses layers "for simplicity."
- **Consistency of contract.** Errors use the same standard error envelope
  and the same centralized exception-to-response mapping already in place
  (`app/core/exceptions.py`) — no new, parallel error-handling path.
- **Data integrity over convenience.** The "comments cannot outlive their
  task" guarantee (FR5, FR6) must hold even under concurrent
  requests/crashes, not just in the happy path of the service layer —
  i.e., it needs to be a property of the stored data, not only of
  well-behaved callers.
- **Read efficiency.** Fetching a task's comments must be an indexed lookup
  by `task_id`, not a full-table scan, so the endpoint stays cheap as the
  total number of comments across all tasks grows.
- **No new operational surface.** No new config, no new external
  dependency, no new background process — comments are served by the same
  app process and the same database as tasks.

## 7. API Requirements

- `POST /v1/tasks/{id}/comments` — create a comment on task `{id}`.
  - Request carries `author` and `message` only; no client-supplied `id`,
    `task_id`, or `created_at` (all server-assigned, matching the
    `<Resource>Create` pattern used for `TaskCreate`).
  - Returns the created comment on success.
  - Fails if task `{id}` does not exist.
  - Fails on missing/invalid `author` or `message`.
- `GET /v1/tasks/{id}/comments` — list the comments belonging to task
  `{id}`.
  - Returns a collection in the `{"data": [...]}` envelope shape already
    used by `TaskList`, for consistency.
  - Fails if task `{id}` does not exist (see Open Questions — the
    alternative of returning an empty list is considered and rejected by
    default, but flagged for confirmation).
  - No pagination, matching the existing `GET /v1/tasks` stance for this
    sample (see Risks for why this sub-resource may outgrow that
    assumption sooner).
- Both routes are nested one level under `/tasks/{id}`, per the existing
  `/v1` versioning and one-level-deep nesting convention — no separate
  top-level `/comments` collection endpoint is introduced.
- No `PUT`, `PATCH`, or `DELETE` route exists for an individual comment
  (FR7) — the framework's default "method not allowed" behavior applies if
  one is attempted.

### Response contracts

High-level only — exact schema field types/constraints are a plan/
implementation detail, not fixed here.

| Endpoint | Status | Response model |
|---|---|---|
| `POST /v1/tasks/{id}/comments` | `201 Created` | A single `Comment` representation (`id`, `task_id`, `author`, `message`, `created_at`) — the `<Resource>Read` shape, mirroring `TaskRead`. |
| `POST /v1/tasks/{id}/comments` | `404 Not Found` | Standard error envelope (`core/api-design.md`), `NOT_FOUND` code — task `{id}` doesn't exist. |
| `POST /v1/tasks/{id}/comments` | `422 Unprocessable Entity` | Standard error envelope — missing/invalid `author` or `message`. |
| `GET /v1/tasks/{id}/comments` | `200 OK` | A collection envelope (`{"data": [Comment, ...]}`, the `<Resource>List` shape, mirroring `TaskList`), ordered per FR4. |
| `GET /v1/tasks/{id}/comments` | `404 Not Found` | Standard error envelope, `NOT_FOUND` code — task `{id}` doesn't exist. |

## 8. Data Model

- A new `Comment` entity, in a many-to-one relationship with `Task`
  (one task has many comments; a comment belongs to exactly one task).
- Fields: `id` (server-assigned identifier), `task_id` (reference to the
  owning task, required), `author` (required text), `message` (required
  text), `created_at` (server-assigned timestamp). No `updated_at` — the
  absence of that field is itself a signal that the resource is immutable.
- The relationship from `Comment` to `Task` is mandatory and enforced as a
  standing constraint, not just validated at creation (FR5): a comment row
  can never reference a task that doesn't exist.
- Deleting a task's row removes its comment rows as an atomic consequence
  (FR6) — the exact mechanism (database-enforced cascade vs.
  application-level cleanup) is deferred to the plan, per Open Questions,
  since both satisfy this spec's requirement.
- `task_id` needs to be efficiently searchable, since "all comments for
  this task" is the only read pattern this spec requires.

**Extensibility.** This spec deliberately builds the smallest viable
`Comment` shape, but the data model and API contract should not paint
future, related features into a corner. Plausible future additions —
attachments on a comment, @mentions inside a comment's `message`,
reactions to a comment — should be addable as new fields, new nested
resources, or new sibling endpoints without changing the meaning of any
field defined here or breaking the `POST`/`GET` contracts above. No such
extension is built now; this is a constraint on today's design, not a
commitment to build any of them later.

## 9. Error Handling

- Reuses the existing domain exception hierarchy and centralized mapping
  (`app/core/exceptions.py`, `core/error-handling.md`) — no new
  error-handling mechanism is introduced.
- "Task not found" for either endpoint maps to the same `NotFoundError`
  concept already used by `GET/PATCH/DELETE /v1/tasks/{id}`, producing the
  existing `NOT_FOUND` error code and `404` status — not a new, comment-
  specific "not found" code.
- Malformed or missing `author`/`message` is a boundary validation failure,
  handled the same way `TaskCreate` validation failures already are (via
  the Pydantic schema layer), not via hand-checking in a service.
- No new error codes are anticipated. If the plan phase identifies a case
  that doesn't fit an existing code, it should be justified there, not
  invented ad hoc in the implementation.

## 10. Testing Requirements

- **Unit tests**: a `CommentService` (or equivalent) tested against a fake
  repository, mirroring the existing `TaskService`/`FakeTaskRepository`
  pattern — covering successful creation, successful listing, and the
  "owning task does not exist" failure path for both operations.
- **Integration tests**:
  - The comment repository against a real (in-memory SQLite, per existing
    convention) session — verifying persistence, the `task_id` lookup, and
    that the integrity constraint from FR5 actually holds at the storage
    layer, not only in the service.
  - The full app via `TestClient` — `POST`/`GET` happy paths, the `404`
    path for a non-existent task on both endpoints, and the `422`/
    validation-error envelope shape for a malformed create request.
  - An explicit end-to-end test that creates a task, adds comments to it,
    deletes the task, and asserts the comments are gone too (FR6) — this
    is the one behavior most likely to be silently wrong if the underlying
    mechanism is implemented at the wrong layer.
- Test data for comments should follow the existing `tests/factories.py`
  convention (a payload factory and a model factory), not hand-built
  dicts/models inline.

## 11. Documentation Requirements

- Root `README.md`'s endpoint listing/table gains the two new routes.
- `CLAUDE.md`'s Project Layout and Routers sections are updated to reflect
  the new resource once it exists, so the "no sub-resources" framing
  currently in the root `spec.md`'s Out of Scope section is corrected —
  that root spec should get a follow-up note pointing at this one.
- The new request/response schemas carry the same level of
  self-documentation (field constraints, docstrings) as `TaskCreate`/
  `TaskRead`, so `/docs` (OpenAPI) reflects the new endpoints without extra
  hand-written API docs.

## 12. Success Criteria

Each item below is written to be checked off, individually, during
implementation review — not a vibe check.

- `pytest` passes, including the new unit and integration tests described
  in Section 10, with zero pre-existing tests broken or modified to
  accommodate the new resource.
- `POST /v1/tasks/{id}/comments` against an existing task returns `201`
  with a body matching the `Comment` response contract in Section 7
  (`id`, `task_id`, `author`, `message`, `created_at` all present and
  correctly populated) — verified against a real request/response, not
  just a unit test double.
- `POST /v1/tasks/{id}/comments` against a non-existent task `id` returns
  `404` with the standard `NOT_FOUND` error envelope — verified by an
  automated test, not just inspection of the code path.
- `POST /v1/tasks/{id}/comments` with a missing or blank `author` or
  `message` returns `422` with the standard error envelope — verified by
  an automated test.
- `GET /v1/tasks/{id}/comments` on a task with N comments (N ≥ 2) returns
  `200` with exactly N entries in the `{"data": [...]}` envelope, ordered
  oldest-first per FR4 — verified by an automated test that asserts the
  order explicitly (not just that all N are present).
- `GET /v1/tasks/{id}/comments` on a task with zero comments returns `200`
  with an empty `data` list (not an error) — verified by an automated
  test.
- `GET /v1/tasks/{id}/comments` against a non-existent task `id` returns
  `404` with the standard error envelope — verified by an automated test.
- Deleting a task that has comments (`DELETE /v1/tasks/{id}`) leaves zero
  rows referencing that `task_id` in the comments store afterward —
  verified directly against the database/repository in an integration
  test, not inferred from the API response alone.
- No `PUT`, `PATCH`, or `DELETE` route exists for `/v1/tasks/{id}/comments/
  {comment_id}` (or equivalent) — attempting one returns the framework's
  default "method not allowed" response, not a custom handler.
- No layering violation: a code review confirms routers stay thin (parse
  request, call one service method, return a schema) and only the
  repository layer touches SQLAlchemy query APIs for comments, matching
  the existing `Task` layering exactly.
- `README.md` and `/docs` (OpenAPI) reflect both new endpoints, confirmed
  by a manual read-through after implementation, per Section 11.

## 13. Risks

- **Unverifiable authorship.** Since there is no authentication anywhere
  in this API (a deliberate, documented scope decision), `author` is a
  free-text string the caller supplies with no verification. Anyone who
  can call the API can leave a comment "as" anyone else. This is an
  inherited risk from the project's existing no-auth stance, not new to
  this feature, but comments make it more visible than task fields do,
  since the field's whole purpose is attribution.
- **Irreversible history loss on task delete.** FR6 means deleting a task
  permanently destroys its comment history with no soft-delete or
  archive. For a feature whose value is largely historical record, this is
  a real tension — worth flagging even though it matches how task deletion
  already works (hard delete, no tombstone).
- **Unbounded growth without pagination.** The existing "no pagination"
  stance for `GET /v1/tasks` is a reasonable simplification for a bounded
  set of tasks. Comments are structurally more likely to accumulate
  without bound on a single, long-lived task — the same simplification is
  proposed here for consistency, but it is more likely to need revisiting
  first for this endpoint than for the task list.
- **Cross-database cascade behavior.** The suite runs against in-memory
  SQLite while production targets Postgres. Foreign-key cascade
  enforcement is not automatically identical between the two (SQLite
  requires it to be explicitly enabled per connection); if the delete
  cascade is implemented in a way that only happens to work under one
  engine, the passing test suite would not guarantee correct behavior in
  production. This needs to be a specific, called-out check in the plan.

## 14. Open Questions

- Should `GET /v1/tasks/{id}/comments` return `404` for a non-existent
  task (this spec's default, for consistency with how `GET /v1/tasks/{id}`
  already behaves), or an empty list? (Owner: plan reviewer — needs a
  decision before the plan is written, since it changes the endpoint's
  contract.)
- Should the task-comment relationship's integrity (FR5/FR6) be enforced
  as a database-level foreign key with cascade delete, or at the
  application/service level? Both satisfy this spec; the choice affects
  the cross-database risk noted in Section 13 and belongs in the plan.
  (Owner: plan author.)
- Is a free-text `author` field (no identity system) acceptable for this
  iteration, or should comment authorship be blocked on some minimal form
  of caller identification first? (Owner: product/spec approver — this
  spec assumes the former, matching the rest of the API's no-auth stance.)
- Does the root `spec.md`'s "sub-resources such as comments... out of
  scope" line need a formal amendment once this spec is approved, or is a
  new spec sufficient on its own? (Owner: spec approver.)

## 15. Out of Scope

- Editing or deleting an individual comment (FR7).
- Pagination, filtering, or alternate sort orders on the comments list —
  the list is always the full, oldest-first set (FR4).
- Any automatic, system-generated activity/audit entries (status changes,
  field edits, etc.) — see Non-goals.
- Threading, replies, reactions, @mentions, or notifications on comments.
- Authentication, authorization, or verified authorship of any kind.
- Rate limiting or abuse prevention on comment creation.
- Alembic or any other migration tooling — consistent with the root
  project's current deferral of migrations; a new `Comment` table is added
  the same way existing tables are (`create_all()` on a fresh database).
- Bulk operations (creating or deleting multiple comments in one request).

---

## Review gate

Approved after architectural review (scope consistency, goals/non-goals
separation, FR completeness, implementation-detail check, API contract
abstraction level, success-criteria measurability, risk/open-question
coverage, and alignment with the existing layered architecture) via
`/approve-spec`. One non-blocking note carried into the plan: the
404-vs-empty-list question for `GET .../comments` on a missing task
(Open Questions) is stated as a firm `404` in the Response contracts and
Success Criteria — the plan should treat that as the working decision
unless explicitly revisited.

Approved by: Nayan1525 (via Claude Code `/approve-spec` review)
Date: 2026-07-06
