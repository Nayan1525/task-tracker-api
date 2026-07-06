# Write an Architecture Decision Record (ADR)

## When to use this

Right after a technical decision affecting this codebase is actually made (adopting Alembic, adding auth, a
schema change) and before the reasoning is lost — not while still debating options.

## Required CLAUDE.md context

The **Project Overview** section of [`CLAUDE.md`](../../CLAUDE.md), plus whichever specific section the
decision touches (e.g. **Migrations** for an Alembic decision).

## Prompt

```
Record this decision as an ADR.

Decision: {{one-sentence summary}}
Why now / trigger: {{the problem or event that forced this decision}}
Options considered: {{list alternatives, even briefly}}
Chosen option and main reason: {{what you picked and why}}
Known tradeoffs being accepted: {{explicit downsides, or "none identified yet"}}

Please:
1. This project has no ADR directory yet — create `decisions/` and use: Title, Status (Proposed/Accepted),
   Context, Decision, Consequences (positive and negative), Alternatives Considered.
2. Write Context neutrally — the situation as it was before the decision, not a justification for it.
3. Give each rejected alternative a concrete, specific reason it was rejected.
4. List Consequences honestly, including negative ones.
5. Flag anything in my input above that's too vague to write a real Consequences section from.
6. Default Status to "Proposed" unless I say it's already agreed.
```

## Tested against

Not executed against this project in this pass. The natural first real ADR for this project, if you want to
try the prompt on something concrete, is exactly the decision `CLAUDE.md`'s Migrations section already
describes needing: adopting Alembic instead of `create_all()`. That gives it real Context to draw from (the
actual limitation already documented) rather than a hypothetical.
