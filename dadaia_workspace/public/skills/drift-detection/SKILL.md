---
name: drift-detection
description: >
  Reference for project-auditor agent. Protocol for comparing specs/memory/*.html
  to actual implementation, dead-code detection methodology, 1–10 compliance
  scoring rubric across 6 dimensions, and dadaia CLI integration.
applyTo: ".dadaia/reports/**"
---

# drift-detection — Memory ↔ Implementation Drift Audit

## TODO

Full content lands in AGT-25 (P3). This stub is sufficient for P2 agent frontmatter
references to resolve.

Outline:
- Memory atom inventory (architecture.html / product/*.html / tech-stack.html).
- Drift detection method: sample-walk per architecture layer, cross-reference
  spec citation vs code citation, file:line on both sides.
- Dead/stale code detection: grep + import-graph + unreachable-layer scan.
- Compliance scoring rubric (1–10) per dimension:
  - architecture, product features, tech-stack, security, test coverage, design.
- Aggregation formula (weighted average + minimum-dimension floor).
- dadaia CLI commands: `dadaia specs doctor`, `dadaia public doctor`,
  `dadaia context show --json`.
- Drift item template (description, evidence, severity, recommendation).
- Recommendation policy: score < 5 on any dimension → recommend hotfix/feature
  release via project-manager.
