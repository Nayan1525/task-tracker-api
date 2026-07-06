# Design a Database Schema for a New Feature

## When to use this

Before writing any model/migration code for a new feature that needs new tables/columns — while the shape of
the data is still a design decision, not yet implementation. Pair with "Generate a Migration" once the design
here is agreed.

## Required CLAUDE.md context

The **Pydantic Models** and **Project Layout** sections of [`CLAUDE.md`](../../CLAUDE.md) — new models need to
land in `app/models/` following `Task`'s existing conventions (naming, timestamp columns, `SAEnum` for
enumerated fields).

## Prompt

```
I need a database schema designed for a new feature: {{one or two sentences describing the feature}}.

Entities involved: {{e.g. "a Task has many Subtasks, each with its own title/status"}}
Access patterns: {{how this data will actually be queried — this drives indexing more than the entities do}}
Expected scale: {{rough row-count/growth expectation, or "unknown, assume moderate"}}
Constraints: {{anything that must always be true — uniqueness, required relationships, valid value ranges}}

Please:
1. Propose the model(s) with columns, types, and nullability — matching app/models/task.py's conventions
   (Mapped[...]/mapped_column, timestamp columns via _utcnow, SAEnum(..., native_enum=False) for enumerated
   fields rather than a bare string).
2. Propose the relationship (FK direction, on-delete behavior) to Task if relevant, and justify the on-delete
   choice against what should actually happen when a Task is deleted.
3. Propose indexes driven by the access patterns above, naming which query each index serves — see
   Task.__table_args__ for where an index like this lives in this project.
4. Call out any constraint that needs an application-level check (in the service layer, per this project's
   layering) versus what the database should enforce directly.
5. Don't write the actual model/migration code yet — stop here for review of the design first.
```

## Tested against

Not executed against this project in this pass. The step-5 stopping point is intentional and worth keeping —
of the two tested database prompts, the ones that skipped straight to code without a design pause produced a
plausible-but-unreviewed result faster, which isn't actually faster once a wrong assumption (e.g. cascade
delete behavior) has to be unwound after the fact.
