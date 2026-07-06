# Plan: Task Comments

Status: Approved
Traces to: [spec.md](./spec.md)
Last updated: 2026-07-06

## Decisions carried from the spec's Open Questions

The spec (§14) leaves two implementation-affecting questions to the plan.
Both are resolved here, not deferred further:

- **404 vs. empty list for `GET .../comments` on a missing task.** The
  spec's Review gate already states the working decision: firm `404`,
  matching `GET /v1/tasks/{id}`. This plan builds to that contract.
- **DB-level FK/cascade vs. application-level enforcement (FR5/FR6).**
  This plan uses a **database-level foreign key with `ON DELETE CASCADE`**,
  not application-level cleanup. Reasoning: NFR §6 requires the "comments
  cannot outlive their task" guarantee to hold "even under concurrent
  requests/crashes... a property of the stored data, not only of
  well-behaved callers" — only a DB-enforced constraint satisfies that:
  app-level cleanup (e.g. deleting comments in the service before deleting
  the task) is not atomic with the task delete and can't survive a crash
  between the two statements or a comment inserted concurrently. The
  tradeoff this creates — SQLite doesn't enforce foreign keys by default,
  Postgres does — is handled explicitly as its own deliverable in
  Milestone 1, per the cross-database risk in spec §13.

## Sequencing principle

Riskiest-assumption-first, then strict bottom-up dependency order. The
single biggest way this feature could pass its test suite and still be
wrong in production is the cross-database cascade-delete behavior flagged
in spec §13 (SQLite vs. Postgres foreign-key enforcement) — so Milestone 1
builds and proves that mechanism in isolation, at the storage layer, before
any business logic or API surface is built on top of it. Milestones 2–3
then follow the existing layering bottom-up (model/repository → service →
schema/router), matching how `Task` itself was built and letting each
milestone depend cleanly on a working layer beneath it. Milestone 4 closes
with the specific end-to-end regression test spec §10 calls out by name,
plus the documentation updates spec §11 requires, so nothing is left
half-wired after the API works.

## Milestone 1 — Comment data model, repository, and FK-enforced cascade delete

Deliverables:
- `app/models/comment.py`: a `Comment` ORM model — `id`, `task_id`
  (`ForeignKey("tasks.id", ondelete="CASCADE")`, indexed), `author`,
  `message`, `created_at`. No `updated_at` (spec §8's immutability signal).
  Registered in `app/models/__init__.py` alongside `Task` so `create_all()`
  picks it up.
- `app/db/session.py`: extract an `enable_sqlite_foreign_keys(engine)`
  helper (a `connect` event listener issuing `PRAGMA foreign_keys=ON`) and
  apply it to the production engine when the URL is SQLite. SQLite ignores
  `ON DELETE CASCADE` unless this pragma is set per connection; Postgres
  enforces FKs natively and is unaffected.
- `tests/conftest.py`: apply the same `enable_sqlite_foreign_keys` helper
  to the in-memory test engine in the `db_session` fixture — the single
  point where the cross-database risk in spec §13 would otherwise go
  unnoticed (a test suite that "passes" only because SQLite silently
  ignored the constraint).
- `app/repositories/comments.py`: `CommentRepository` with `create(...)`
  and `list_for_task(task_id)` (ordered `created_at asc, id asc` — FR4,
  ties broken deterministically).
- `tests/factories.py`: `make_comment_payload()` and `make_comment_model()`
  following the existing `make_task_*` convention.

Acceptance criteria:
- New integration test `tests/integration/test_comment_repository.py`:
  creates a task, adds ≥2 comments via `CommentRepository`, deletes the
  task via `TaskRepository.delete`, then queries comments by `task_id`
  directly and asserts zero rows remain — proving the DB-level cascade
  actually fires under the same SQLite engine/config the full suite uses.
- A second test in that file asserts inserting a `Comment` row with a
  `task_id` that doesn't exist raises an `IntegrityError` from the
  database itself (FR5 as a standing constraint, not just an app-level
  check) — committed directly through the session, bypassing any service.
- `list_for_task` on a task with 0 comments returns `[]`; with N≥2
  comments returns them in creation order (FR4).
- `pytest` passes.

Depends on: nothing (first slice).

## Milestone 2 — CommentService

Deliverables:
- `app/services/comments.py`: `CommentService(task_service: TaskService,
  comment_repository: CommentRepository)`. `create(task_id, payload)` and
  `list(task_id)` both call `task_service.get(task_id)` first — reusing
  the `NotFoundError` `TaskService.get` already raises (FR2/FR5) instead
  of duplicating an existence check against `TaskRepository` directly.
- `tests/unit/test_comment_service.py`: `CommentService` against a
  `FakeCommentRepository` and the existing `FakeTaskRepository`-backed
  `TaskService` (or an equivalent fake), mirroring
  `tests/unit/test_task_service.py`'s pattern.

Acceptance criteria:
- Unit tests cover: successful create (returns a comment with `id`/
  `created_at` populated); create against a non-existent `task_id` raises
  `NotFoundError`; list returns comments in insertion order; list against
  a non-existent `task_id` raises `NotFoundError`; list on a task with
  zero comments returns `[]`, not an error.
- No test in this milestone touches a real database or the FastAPI app
  (unit tier stays framework- and DB-free, per `CLAUDE.md`'s Testing
  section).
- `pytest` passes.

Depends on: Milestone 1.

## Milestone 3 — Schemas and API endpoints

Deliverables:
- `app/schemas/comment.py`: `CommentCreate` (`author: Field(min_length=1,
  max_length=100)`, `message: Field(min_length=1, max_length=2000)` — FR8,
  bounded and non-blank, mirroring `TaskCreate`'s constraint style),
  `CommentRead` (`id`, `task_id`, `author`, `message`, `created_at`,
  `ConfigDict(from_attributes=True)`), `CommentList` (`data:
  list[CommentRead]`).
- `app/api/deps.py`: `get_comment_service` provider — `get_db` →
  `CommentRepository(db)` + the existing `get_task_service` → 
  `CommentService`.
- `app/api/v1/routers/comments.py`: `APIRouter(prefix=
  "/tasks/{task_id}/comments", tags=["comments"])` with:
  - `POST ""` → `201`, `Location` header (`/v1/tasks/{task_id}/comments/{id}`),
    `responses={404: {"model": ErrorResponse}}`.
  - `GET ""` → `200`, `CommentList`, `responses={404: {"model":
    ErrorResponse}}`.
  Handlers stay thin/sync `def`, one service call each, matching
  `app/api/v1/routers/tasks.py`'s pattern exactly. No `PUT`/`PATCH`/
  `DELETE` route is defined (FR7) — the framework's default 405 applies.
- `app/api/v1/__init__.py`: `include_router(comments.router)` alongside
  `tasks.router`.

Acceptance criteria:
- `tests/integration/test_comments_api.py` (new): `POST` on an existing
  task returns `201` with the full `Comment` body; `POST` on a
  non-existent `task_id` returns `404` with the standard `NOT_FOUND`
  envelope; `POST` with a missing/blank `author` or `message` returns
  `422` with the standard envelope.
- `GET` on a task with N≥2 comments returns `200` with exactly N entries
  in `{"data": [...]}`, asserted in oldest-first order explicitly (not
  just membership); `GET` on a task with 0 comments returns `200` with
  `{"data": []}`; `GET` on a non-existent `task_id` returns `404`.
- A request to `DELETE /v1/tasks/{id}/comments/{comment_id}` (or `PUT`/
  `PATCH`) returns `405`, asserted by a test.
- Manual check: `/docs` lists both endpoints with the schema field
  constraints visible.
- `pytest` passes.

Depends on: Milestone 2.

## Milestone 4 — End-to-end cascade regression test and documentation

Deliverables:
- Extend `tests/integration/test_comments_api.py` (or a dedicated test)
  with the exact scenario spec §10 calls out: create a task via the API,
  add comments to it via the API, `DELETE /v1/tasks/{id}`, then assert
  directly against the repository/session (not just the API) that zero
  comment rows remain for that `task_id`.
- `README.md`: add `POST /v1/tasks/{id}/comments` and
  `GET /v1/tasks/{id}/comments` to the endpoint listing/table.
- `CLAUDE.md`: update Project Layout (new `comments.py` files across
  `models/`, `schemas/`, `services/`, `repositories/`,
  `api/v1/routers/`) and the Routers section to describe the nested
  `/tasks/{id}/comments` router.
- Root `spec.md`: add a one-line follow-up note in its Out of Scope
  section pointing at `.claude/specs/task-comments/spec.md`, correcting
  the now-stale "Sub-resources such as comments... out of scope" line
  (resolves spec §14's amendment question — a pointer note, not a formal
  rewrite of the approved root spec).

Acceptance criteria:
- The new end-to-end test fails if `ondelete="CASCADE"` is removed from
  the `Comment` model (checked manually once during this milestone's
  review, then left in place) — confirming it actually exercises the
  cascade rather than passing vacuously.
- `README.md`'s table lists both new routes.
- `CLAUDE.md`'s Project Layout/Routers sections mention the comments
  resource and its files.
- `spec.md`'s Out of Scope section links to the new spec.
- Full `pytest` run is green with **zero** pre-existing tests modified
  (spec §12 success criteria) — a diff to any existing test file at this
  point is a signal something in Milestones 1–3 leaked into `Task`'s
  behavior.

Depends on: Milestone 3.

## Review gates

Review happens after every milestone, each landed as its own commit (or
short PR). "Review" means: `pytest` passes in full, and for Milestones 3
and 4 specifically, the endpoints are exercised for real against a running
app (`/docs` or a manual `curl`/`httpx` call), not just asserted by the
test suite — matching this repo's `verify` skill expectation that a
runtime surface gets driven, not only type-checked or unit-tested. No
milestone starts before the previous one's tests are green.

## Out of scope for this plan

Nothing in the spec's Scope (§3) or Functional Requirements (§5) is
deferred — Milestones 1–4 cover FR1–FR8, the API contract in §7, the data
model in §8, and the documentation requirements in §11 in full. Everything
in the spec's own §15 Out of Scope (comment editing/deletion, pagination,
threading, auth, rate limiting, Alembic, bulk operations) remains out of
scope for this plan too, unchanged — this plan builds exactly the surface
the spec defines, no more.

---

## Review gate

Approved: implementation strategy and milestone sequencing are consistent
with the approved spec, preserve the Router → Service → Repository → Model
layering, and resolve both Open Questions (§14 of the spec) as documented
above. Proceed with implementation per Milestones 1–4.

Approved by: Nayan1525 (via Claude Code plan review)
Date: 2026-07-06
