# Audit a Single Function

## When to use this

Reviewing one specific function/method in depth — before reusing its pattern elsewhere, or when it's suspected
of a bug — not a whole-file or whole-PR review (use `review-pr.md` for that).

## Required CLAUDE.md context

The **Testing** and **Routers**/**Dependency Injection** sections of [`CLAUDE.md`](../../CLAUDE.md) — so
"does this follow this project's conventions" and "is this covered by an existing test" can be checked against
something concrete.

## Prompt

```
Audit {{function/method, with file path}} in depth.

Context: {{what it's supposed to do, and why you're auditing it now}}

Please check, citing specific line(s) for anything you flag:
1. Correctness — does it do what its name/callers assume for all inputs, not just the obvious ones? Consider
   empty/None/boundary inputs explicitly.
2. Error handling — does it fail loudly and specifically on invalid input/state, or could it silently return a
   wrong result or swallow an exception?
3. Side effects — are they all intentional and visible from the signature?
4. Consistency — does it follow this project's conventions (e.g. raising AppError subclasses from
   app/core/exceptions.py rather than a bare exception, matching the pattern in app/services/tasks.py)?
5. Test coverage — is this function's actual behavior (not just its happy path) covered in tests/unit/ or
   tests/integration/? If not, say exactly what's missing.

Rank findings by severity (would cause a wrong result/crash vs. a maintainability nit) and don't invent issues
you can't point to concretely in the code.
```

## Tested against

Not executed against this project in this pass — `check-security.md` in this same category was the one tested
live. If you run this one against `TaskService.update` (the natural target, since it's the one method with the
most branching), pay attention to the `exclude_unset` short-circuit at `app/services/tasks.py:49-50` — it's
already covered by a test as of this pass (see `testing/generate-unit-test.md`), so don't flag it as an
untested gap.
