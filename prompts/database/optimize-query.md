# Optimize a Slow Database Query

## When to use this

A specific query is confirmed or reasonably suspected slow because of table growth — not a speculative "make
the DB faster" ask. Bring the actual query and why you think it's slow (row counts, a plan, a timing); this
prompt won't go looking for problems that haven't been reasoned about first.

## Required CLAUDE.md context

The **Migrations** section of [`CLAUDE.md`](../../CLAUDE.md) — this project has no Alembic yet, so a schema
change (like an index) is a change to the SQLAlchemy model, not a migration file, and won't affect an existing
table's data via `create_all()`.

## Prompt

```
This query is slow and needs optimizing: {{the query, or the ORM call that generates it — e.g.
"TaskRepository.list() filtered by status"}}.

Evidence it's slow / why it will be: {{e.g. "no index on the filtered column, and the table is expected to
grow past {{N}} rows"}}
Table/row counts involved: {{approximate, current and expected}}

Please:
1. Identify the specific cause (missing index causing a sequential scan, an avoidable join, a non-sargable
   WHERE clause) rather than a generic "add caching" suggestion.
2. Propose the smallest fix — usually an index — and explain the tradeoff (extra write cost on every
   insert/update to the indexed column).
3. Add the index directly on the relevant SQLAlchemy model in app/models/ (e.g. via `Index(...)` in
   `__table_args__`, see Task.__table_args__ for the existing pattern) — this project has no Alembic yet, so
   there's no migration file to generate; `create_all()` will pick it up for a fresh database.
4. Note explicitly that `create_all()` will NOT add this index to a database that already has the `tasks`
   table created — if this needs to reach an existing environment, say so and flag that Alembic (or a manual
   `CREATE INDEX`, tracked somewhere) would be needed instead.
5. Run the test suite afterward to confirm nothing broke.
```

## Tested against

**Ran directly against this repo.** `TaskRepository.list()` filters by `status` (`app/repositories/tasks.py`)
but `Task.status` had no index — every status-filtered query was a full table scan, and the only filter this
endpoint supports is on `status`. Added `Index("ix_tasks_status", "status")` via `Task.__table_args__` in
`app/models/task.py`. Ran `pytest`: 30/30 passed (no regression; SQLite's `create_all()` applies the new index
the same as Postgres's would on a fresh database). Confirms the prompt's step 3/4 split is the real nuance
here — this fix is free on a fresh DB but would need a real migration mechanism to reach an existing one,
which this project doesn't have yet. No wording changes needed.
