# Generate a Unit Test

## When to use this

A function/method in `app/services/` (or a schema in `app/schemas/`) has real logic — branching, validation —
with no test or a real gap. Not for something that needs a real DB/network to exercise meaningfully; that's an
integration test.

## Required CLAUDE.md context

The **Testing** section of [`CLAUDE.md`](../../CLAUDE.md) — specifically the `FakeTaskRepository` convention
(no real DB in a unit test) and where unit tests live (`tests/unit/`).

## Prompt

```
Write unit test(s) for {{function/method, with file path — e.g. "TaskService.update in app/services/tasks.py"}}.

What it does: {{one sentence, or "figure it out from the code"}}
Coverage gap: {{what's not currently tested — a specific branch, edge case, or "no tests exist yet"}}

Please:
1. Read tests/unit/test_task_service.py first and confirm the gap you're about to fill isn't already covered
   — if it is, tell me and pick a different one rather than duplicating an existing test.
2. Test through the public interface only — no asserting on private/internal state.
3. Use this project's existing FakeTaskRepository (in tests/unit/test_task_service.py) rather than a mocking
   library — extend it if the method under test needs something it doesn't yet provide.
4. Cover the specific gap precisely — don't re-test branches already covered by existing tests just to pad
   coverage.
5. One behavior per test function, named for the behavior (test_returns_x_when_y, not test_update_2).
6. Run `pytest tests/unit -q` after writing these and show me the result.
```

## Tested against

**Ran directly against this repo.** Read `tests/unit/test_task_service.py` and found a real gap: every
existing test for `TaskService.update` sets at least one field, so the `if not fields: return task`
short-circuit at `app/services/tasks.py:49-50` (an empty `TaskUpdate()` payload) was never exercised. Added
`test_update_with_no_fields_set_returns_task_unchanged` to `tests/unit/test_task_service.py`. Ran `pytest`:
30/30 passed (was 29). Confirms step 1's instruction to check for an existing gap first is the one that
matters most — a version of this prompt without that check would happily re-test an already-covered branch
and produce a redundant test instead of closing a real gap.
