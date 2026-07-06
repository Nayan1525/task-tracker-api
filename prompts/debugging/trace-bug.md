# Trace a Bug to Its Root Cause

## When to use this

Something produces a wrong result with no exception thrown — the code runs, but the output is incorrect — and
you need to find where reality diverges from the intended logic, not just patch the symptom you noticed.

## Required CLAUDE.md context

The **Routers**, **Dependency Injection**, and **Testing** sections of [`CLAUDE.md`](../../CLAUDE.md) — tracing
a bug in this project means walking router → service → repository, and the fix should land as a permanent
regression test using this project's existing fixtures.

## Prompt

```
This is producing a wrong result with no error/exception:

Observed: {{what actually happens — specific}}
Expected: {{what should happen instead}}
Steps to reproduce: {{exact input/request that triggers it}}
Where I think the problem might be: {{a hunch, or "no idea, start from the entry point"}}

Please:
1. Reproduce it first — run the steps above, or write a minimal failing test using this project's existing
   fixtures (tests/conftest.py) — before proposing any explanation.
2. Trace the actual data/control flow from the router through the service (app/services/) to the repository
   (app/repositories/) until you find the exact point where the observed value diverges from expected.
3. Identify the root cause, not just the first line where the wrong value appears.
4. Show me the root cause and the failing test/repro before writing a fix.
5. Once confirmed, fix it and turn the repro into a permanent test in tests/unit/ or tests/integration/,
   whichever layer actually exhibits the bug.
```

## Tested against

Not executed against this project in this pass. Note for whoever runs it here: this project's `TaskRepository`
methods (`app/repositories/tasks.py`) are the only layer touching SQLAlchemy directly — if a filtering bug
exists, it's almost always in the `stmt.where(...)` construction there, not in the service or router, since
those layers just pass the value through.
