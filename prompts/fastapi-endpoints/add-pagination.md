# Add Pagination to a FastAPI List Endpoint

## When to use this

`GET /v1/tasks` currently returns every task with no limit — fine at demo scale, not once the table can
realistically grow. Use this once that growth is a real concern, not preemptively on day one (`spec.md` lists
pagination as explicitly out of scope for the sample as it stands).

## Required CLAUDE.md context

The **Pydantic Models** and **Routers** sections of [`CLAUDE.md`](../../CLAUDE.md) — specifically the
`<Resource>List` wrapper convention (`TaskList.data`) so the new response shape doesn't invent a
second, inconsistent convention.

## Prompt

```
Add pagination to GET /v1/tasks (app/api/v1/routers/tasks.py).

Style: limit/offset via query params
Default/max page size: {{e.g. "default 20, max 100"}}

Please:
1. Add `limit`/`offset` query parameters via FastAPI's Query() with sane defaults and a constraint enforcing
   the max page size — reject (422) an out-of-range value, don't silently clamp it.
2. Extend TaskList (app/schemas/task.py) to include `total` and the pagination params used, alongside the
   existing `data` field — match TaskList's existing field naming, don't rename `data` to something else.
3. Push limit/offset down into TaskRepository.list()'s query itself (app/repositories/tasks.py) — never fetch
   every row and paginate in Python.
4. TaskRepository.list() already orders by `created_at.desc(), id.desc()` — keep using that as the stable sort
   key for pagination so page boundaries don't shift between requests.
5. Update tests/integration/test_tasks_api.py and tests/unit/test_task_service.py to cover: the default page,
   an offset beyond the data available (empty `data`, not an error), and an out-of-range limit (422).
6. Update the endpoint's OpenAPI description so the new query params show up correctly at /docs.
```

## Tested against

Not executed against this project in this pass. Note going in: `TaskList`'s existing field is named `data`,
not `items` — if you've seen a generic version of this prompt elsewhere that says "return a wrapper with an
`items` field," don't apply that literally here; it would rename an existing, already-used response field for
no reason related to pagination. This prompt has already been corrected to say `data` to match what's actually
in this repo.
