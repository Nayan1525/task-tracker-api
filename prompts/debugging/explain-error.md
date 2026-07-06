# Explain an Error

## When to use this

You have a traceback/error message you don't immediately understand and want it explained in the context of
*this* codebase — not a generic explanation of the exception type from documentation.

## Required CLAUDE.md context

The **Project Layout** section of [`CLAUDE.md`](../../CLAUDE.md) so Claude can map a traceback frame to the
right layer (router/service/repository/model) instead of guessing.

## Prompt

```
Explain this error in the context of this codebase:

{{paste the full traceback/error message, not just the last line}}

What I was doing when it happened: {{the request/command/action that triggered it}}
What I expected instead: {{expected behavior}}

Please:
1. Identify exactly where in this codebase (file:line) the error originates, tracing through the actual call
   stack shown — not a guess based on the exception type alone.
2. Explain why it happens here specifically — the actual condition in this code that leads to it.
3. Tell me if this is a symptom of a deeper issue (e.g. a bad assumption earlier in the call chain — router →
   service → repository → model) versus self-contained at the line that raised it.
4. Don't propose a fix yet unless I ask — confirm I understand what's happening first.
```

## Tested against

Not executed against this project in this pass. This project's own error handling is relevant context:
`app/core/exceptions.py`'s `to_error_response` already distinguishes 5xx (logs full traceback, returns a
generic client-facing message) from 4xx (real message + details) — an error explained via this prompt should
be read against the *server-side log*, not the client response, when it's a 5xx, since the response body is
intentionally generic.
