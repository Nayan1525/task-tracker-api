---
description: Review and approve a feature specification.
argument-hint: <path-to-spec>
---

Review the specification at:

$ARGUMENTS

Perform a thorough architectural review.

Verify:

- Scope is internally consistent.
- Goals and non-goals are clearly separated.
- Functional requirements are complete.
- No implementation details appear in the specification.
- API contracts are defined at the correct abstraction level.
- Success criteria are measurable.
- Risks and assumptions are documented.
- Open questions are appropriate.
- The specification aligns with the existing project architecture.

If issues are found:

- Explain each finding.
- Classify severity.
- Recommend **Revise**.

If no blocking issues remain:

Return:

- Review Summary
- Findings
- Recommendation
- Approval Decision

If approved, instruct Claude to proceed with generating the implementation plan.