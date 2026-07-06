# Generate an Integration Test

## When to use this

Testing behavior that only shows up when real collaborators are wired together — the repository against a
real (test) database, or a full request through router → service → repository — after the unit-level logic is
already covered.

## Required CLAUDE.md context

The **Testing** section of [`CLAUDE.md`](../../CLAUDE.md) — specifically the `client`/`db_session` fixtures in
`tests/conftest.py` and the factories in `tests/factories.py`.

## Prompt

```
Write integration test(s) for {{the endpoint or repository method}}.

Scenario(s) to cover: {{e.g. "filtering by status with zero matches", "an invalid status query value"}}

Please:
1. Read tests/integration/test_tasks_api.py and tests/integration/test_task_repository.py first and confirm
   your scenario isn't already covered — if it is, pick a genuinely uncovered one instead.
2. Use the existing `client`/`db_session` fixtures (tests/conftest.py) and `make_task_payload`/
   `make_task_model` factories (tests/factories.py) — don't hand-build payloads or stand up a second way of
   creating test data.
3. Test the actual contract: real HTTP status codes and response bodies (matching the error envelope from
   app/core/exceptions.py for failure cases), not internals.
4. Assert both the success path and at least one failure/edge case from the scenarios above.
5. Run the full test suite afterward (not just the new tests) and confirm the count only went up, nothing
   else broke.
```

## Tested against

Not executed against this project in this pass. Step 1 exists because the obvious example scenario for this
project — "delete then verify 404" — is **already covered**
(`tests/integration/test_tasks_api.py::test_delete_task_returns_204_then_404`, confirmed by reading the file):
a prompt that doesn't check first risks "confirming" a gap that isn't real.
