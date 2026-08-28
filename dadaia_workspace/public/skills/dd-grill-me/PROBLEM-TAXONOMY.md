# PROBLEM-TAXONOMY — dd-grill-me

Disclosed reference reached during Step 1 (inspect before asking): the problem shapes that destroy specs.
Named so a gap can be classified before it resolves by inspection or promotes to the design tree.

| Problem type | Example |
|---|---|
| Inconsistency between specs | `feature/my-feature` references paths from `platform/my-platform`, but that feature is not done yet |
| Spec vs implementation (drift) | A spec's security section says socket `:ro`, but the service needs write access |
| Open question answerable by code | "What is the operator ID?" — it is already in the service env file |
| Divergent naming | `ALLOWED_IDS` in one spec vs `OWNER_ID` in another — same concept, two names |
| Ambiguous syntax | `{{VAR}}` in a config template, but the substitution tool uses `${VAR}` |
| Undeclared dependency | `feature/my-feature` depends on `platform/my-platform`; the dependency is not declared |
| Incorrect category | A feature named "guardrails" actually specifies config backups |
| Stale constitution | `constitution.md` names Provider A as primary; a later release shipped Provider B |

- Priority order when several gaps compete for the same round: gaps that block implementation first.
- Priority order (continued): then spec-vs-code drift, then order dependencies, then naming, then unanswerable ACs, then a stale constitution.
