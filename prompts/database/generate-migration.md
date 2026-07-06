# Generate a Database Migration

## When to use this

This project does **not have Alembic yet** — schema changes currently ship via `Base.metadata.create_all()` at
startup (see `CLAUDE.md`'s Migrations section), which only works for a fresh database. Use this prompt either
to introduce Alembic in the first place, or (once it exists) to generate a migration for a model change that
needs to reach a database that already has data in it.

## Required CLAUDE.md context

The **Migrations** section of [`CLAUDE.md`](../../CLAUDE.md) in full — it documents the current
`create_all()`-based state and the explicit warning against calling Alembic from app startup once it exists.

## Prompt

```
{{If Alembic doesn't exist yet:}} Introduce Alembic to this project and generate the initial migration
capturing the current schema (the Task model, and anything else in app/models/ at the time).

{{If Alembic already exists:}} Generate a migration for this schema change: {{describe the change, or paste
the updated model code}}.

Does this need a data backfill? {{yes/no; if yes, describe what existing rows need}}
Is this reaching a database that already has real data in it? {{yes/no}}

Please:
1. If setting up Alembic for the first time: wire alembic/env.py to import app.models (so every model is
   registered on Base.metadata) and pull the DB URL from app.core.config.get_settings().database_url — never
   a hardcoded URL.
2. Generate the migration via `alembic revision --autogenerate`, then show me the generated file — autogenerate
   misses renames and some constraint/data changes, so I need to review what it inferred.
3. If a backfill is needed on a table with real data, split it into separate migrations: add the column
   nullable → backfill → a later migration to enforce NOT NULL/drop the old column.
4. Confirm the migration has a working `downgrade`.
5. If this is the first Alembic migration and the app still calls `init_db()` (which calls `create_all()`) at
   startup, flag that conflict explicitly and tell me what you'd change — don't silently leave both in place
   or silently remove one without confirming.
6. Never hand-edit a migration that's already been applied to a shared environment — if fixing a past
   migration, generate a new one instead.
```

## Tested against

Not executed against this project in this pass. Step 5 is the sharpest edge if you do run this here: this
project's `create_all()` call in `app/main.py`'s lifespan and a newly-introduced Alembic setup will conflict
(both would try to create the same tables) unless one is explicitly removed — don't let the prompt's output
leave both silently coexisting.
