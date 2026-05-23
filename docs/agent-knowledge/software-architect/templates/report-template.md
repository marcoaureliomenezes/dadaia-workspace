# software-architect — Report Templates

This file is referenced from `dadaia_workspace/public/agents/software-architect.md`.
It contains the canonical report templates for each operating mode (ONBOARD, DRAFT,
REVIEW, plus the workspace-level overview).

Render each template into `.dadaia/reports/<context>/software-architect/<timestamp>-<mode>.html`
(HTML emission) when the dispatch explicitly requests `--with-report`. The structure below
is shown in markdown for readability; convert sections to HTML semantically when emitting.

---

## `<timestamp>-onboard.md` (per repo)

```markdown
# Architecture Onboarding Report: <repo-name>
Date: <ISO 8601>
Repo: repos/<slug>/
Architect: software-architect (first review)

## Project Understanding
<What this project does — architect own words after reading specs + code.
If the project purpose is unclear after inspection, say so explicitly.>

## Architecture Status
- Declared architecture: YES (architecture.html + foundation/SPEC.md) | PARTIAL | NO
- Implementation found: YES | PARTIAL | NO
- Alignment: ALIGNED | PARTIAL DRIFT | SIGNIFICANT DRIFT | UNDETERMINED

## Declared Architecture Summary
<Key layers, modules, and dependency rules as stated in specs.
"None declared" if no architecture document exists.>

## What the Code Actually Does
<Architect read of the actual structure, modules, and dependencies found in the code.>

## Gap Analysis

### [CRITICAL] <gap title>
Location: <file:line or module>
Issue: ...
Why it matters: ...
Trade-off if fixed: ...
Recommendation: ...

### [HIGH] ...
### [MEDIUM] ...
### [LOW] ...

## Missing Architecture Documentation
<Architectural decisions that should be written down but are not — even if the code looks fine.
Without these, future developers will make inconsistent choices.>

## Improvement Backlog
| # | Priority | Item | Why | Trade-off | Effort |
|---|---|---|---|---|---|
| 1 | P1 | ... | ... | ... | S |
| 2 | P2 | ... | ... | ... | M |

Priority: P1 = blocks next feature / active risk, P2 = debt accumulating, P3 = deferred safely.
Effort: S = hours, M = days, L = weeks.

## Open Questions (via dadaia-grill-me)
<Questions answered by the operator. Include the question and the answer received.
If no questions were needed: "None — all questions answered by inspection.">

## Recommended Next Steps
<Ordered by impact. The first item must be the one that unblocks everything else.>
```

---

## `<timestamp>-workspace-overview.md`

```markdown
# Workspace Architecture Overview
Date: <ISO 8601>
Repos scanned: <N> (<list of slugs>)

## Architecture Maturity by Repo
| Repo | Status | Biggest Gap | Priority |
|---|---|---|---|
| dadaia-workspace | DEFINED | ... | P1 |
| redacted-slug | IMPLICIT | ... | P2 |
| ... | | | |

## Cross-Repo Patterns (Shared Problems)
<Issues that appear in multiple repos. Cross-cutting problems are higher priority
because fixing them once can benefit all projects.>

## Systemic Risks
<Issues that compound across the workspace — e.g., no consistent error handling standard,
divergent patterns for the same problem, no shared testing contract.>

## Recommended Order of Attack
<If the team can only fix one thing per sprint, this is the sequence and why.>
```

---

## `<timestamp>-draft.md` (new project)

```markdown
# Architecture Draft: <Project Name>
Date: <ISO 8601>
Context: <context-name>

## Summary
One paragraph: what the project does and the key constraints that shaped this architecture.

## Proposed Architecture
- Layer diagram and responsibilities
- Module structure with clear ownership
- Dependency rules

## Critical Design Decisions
For each decision: options considered, chosen approach, why.
Trade-off: what this decision costs and what it prevents.

## Risk Areas
Where the architecture is most likely to degrade under growth or parallel development.

## Open Questions
Questions that must be resolved before implementation begins.
```

---

## `<timestamp>-review.md` (single project audit)

```markdown
# Architecture Review: <Project Name>
Date: <ISO 8601>
Context: <context-name>
Verdict: PASS | FAIL | CONDITIONAL

## Executive Summary
One paragraph: overall health of the architecture in this codebase.

## Findings

### [CRITICAL] <title>
Location: <file:line>
Issue: ...
Why it matters: ...
Trade-off if fixed: ...
Recommendation: ...

### [HIGH] ...
### [MEDIUM] ...
### [LOW] ...

## Stale and Dead Code
Exhaustive list. No item too small to mention.

## OOP & Design Pattern Audit
### SOLID Violations
### Misapplied Patterns
### Anti-patterns
### Refactoring Recommendations (ordered by ROI)

## Improvement Backlog
| # | Priority | Item | Why | Trade-off | Effort |
|---|---|---|---|---|---|

## Verdict Rationale
Why this codebase passes, fails, or passes with conditions.

## Required Actions Before Next Increment
Ordered list of changes that must happen before new features are built.
```
