# Review a Pull Request / Diff

## When to use this

Reviewing a complete, ready-for-review change (a working diff) before merge — broader than a single-function
audit, covering correctness, tests, and scope together.

## Required CLAUDE.md context

All of [`CLAUDE.md`](../../CLAUDE.md) — a real diff on this project usually touches multiple layers (router +
schema + service + repository) at once, so the reviewer needs the whole picture, not one section.

## Prompt

```
Review this diff before merge.

{{paste the diff, e.g. output of "git diff"}}

Please review for:
1. Correctness & design — does the change do what it claims, and does it fit this project's existing layering
   (router → service → repository → model, per CLAUDE.md) rather than introducing a new pattern?
2. Tests — is new/changed behavior covered in tests/unit/ and/or tests/integration/ as appropriate? Is anything
   conspicuously untested?
3. Error handling — do failure paths raise this project's AppError subclasses (app/core/exceptions.py) rather
   than a bare exception or an unhandled case?
4. Security — anything from unvalidated input or a secret touched by this diff? (See check-security.md for a
   deeper pass if this diff touches auth or untrusted input directly.)
5. Scope — does the diff do what it claims and nothing more — no unrelated refactors bundled in?

Classify each finding as **Blocking** (correctness bug, missing test for new behavior, security issue, or a
violation of an established convention in CLAUDE.md) or **Nit** (style preference, minor improvement). Cite
file:line for every finding. If a category has no issues, say so explicitly rather than skipping it.
```

## Tested against

Not executed against this project in this pass — `check-security.md` in this same category was the one tested
live, against real code rather than a synthetic diff. If you run this one here, the cheapest way to validate it
is the same technique: make one small, deliberately-imperfect change (e.g. a new query param with a missing
`max_length` constraint, unlike every other string field in `app/schemas/task.py`), diff it, and confirm the
review actually catches that specific, real inconsistency rather than producing generic praise.
