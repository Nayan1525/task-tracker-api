# Generate a New FastAPI Endpoint

## When to use this

Adding a new resource or route to this service, following the layering it already has. Not for the
project's first endpoint (there isn't one to imitate) — that's a scaffolding decision, not a generate-endpoint
one.

## Required CLAUDE.md context

The **Project Layout**, **Routers**, **Pydantic Models**, and **Dependency Injection** sections of
[`CLAUDE.md`](../../CLAUDE.md) — Claude needs to know the router/schema/service/repository split and the
`api/deps.py` provider pattern to place new code consistently instead of inventing a shape for it.

## Prompt

```
I need a new endpoint added to this FastAPI service.

Resource/feature: {{resource name, e.g. "task comments"}}
Operation(s): {{e.g. "POST /tasks/{task_id}/comments to add a comment, GET to list them"}}
Fields: {{list the fields the request/response need, with types and which are optional}}
Business rules: {{anything beyond basic CRUD — ownership checks, status restrictions, etc., or "none"}}

Follow this project's existing layering exactly as it already exists for the Task resource (use
app/api/v1/routers/tasks.py, app/services/tasks.py, app/repositories/tasks.py, app/schemas/task.py as the
reference — don't invent a new pattern):
1. Add the Pydantic schemas for the request and response shapes in app/schemas/.
2. Add the repository method(s) needed in a new app/repositories/<resource>.py.
3. Add the service method(s) containing the business logic in a new app/services/<resource>.py, raising this
   project's existing domain exceptions (from app/core/exceptions.py) for failure cases — never a raw
   FastAPI/framework error.
4. Add the router handler(s) in a new app/api/v1/routers/<resource>.py — thin: parse/validate, call the
   service, return the schema. Plain `def`, not `async def`, matching this project's sync-SQLAlemy convention.
5. Wire a dependency provider in app/api/deps.py (get_<resource>_service) following the get_task_service
   pattern, and register the router in app/api/v1/__init__.py.
6. Add tests at the same layers this project already tests at: a unit test for the service against a fake
   repository (see tests/unit/test_task_service.py's FakeTaskRepository), and integration tests via the
   `client`/`db_session` fixtures (see tests/integration/test_tasks_api.py).

Show me the plan (files to touch, in order) before writing code if the change touches more than 3 files.
```

## Tested against

Not executed against this project in this pass — see `prompts/README.md` for which 3 prompts were tested
live. Before relying on it for a real change, run it once and fold back anything you learn (this project's
convention for handling a required-parent-resource check like "task must exist" belongs in the service, per
`NotFoundError`'s existing use in `TaskService.get` — confirm the generated code does that rather than
duplicating the check in the router).
