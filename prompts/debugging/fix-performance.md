# Fix a Performance Problem

## When to use this

A specific operation is measurably slower than it should be and you have at least rough evidence of that — not
a general "make it faster" ask with no target.

## Required CLAUDE.md context

The **Routers** section of [`CLAUDE.md`](../../CLAUDE.md) (handlers here are sync `def`, not `async def` — a
common false lead is assuming an async-event-loop-blocking issue that can't actually occur in this codebase)
and the **Migrations** section (the other common real cause: a missing index, see `optimize-query.md`).

## Prompt

```
{{operation, e.g. "GET /v1/tasks"}} is slower than it should be.

Evidence: {{timing numbers, or "takes Nms for N tasks, should be roughly constant"}}
Recent changes nearby, if any: {{anything that changed recently, or "none I know of"}}

Please:
1. Reason from the evidence to find the actual bottleneck first — don't optimize the first thing that looks
   slow by inspection.
2. Check the usual suspects for this specific stack, in likelihood order: a missing index (this project's
   TaskRepository.list() only filters on `status` — check app/models/task.py for whether that column is
   indexed), an N+1 pattern, or an algorithmically bad loop. Rule out async-event-loop blocking explicitly —
   this project's handlers are synchronous `def` run in FastAPI's threadpool, not `async def`, so that specific
   failure mode doesn't apply here.
3. Propose the fix with the smallest blast radius that addresses the measured cause.
4. Quantify the expected improvement (query count, latency, or Big-O change) before and after.
5. Add a regression test/assertion (e.g. a query-count check) that would catch this specific regression coming
   back.
```

## Tested against

Not executed against this project in this pass, though it overlaps with what `optimize-query.md` already
proved out here: the one real performance gap found by directly reading this codebase was the missing index on
`Task.status` (now fixed — see `database/optimize-query.md`'s Tested against note). If you run this prompt
here today, expect it to correctly point at the same thing rather than inventing an async-blocking issue that
doesn't apply to this project's sync handlers.
