---
name: architecture-code-review
description: >
  Reference for code-reviewer agent. Defines the 6-axis review checklist
  (architecture, patterns, tests, security smells, perf smells, dead code),
  OOP/SOLID violation patterns, complexity heuristics, and report templates.
applyTo: ".dadaia/reports/**"
---

# architecture-code-review — PR/Branch Review Reference

## TODO

Full content lands in AGT-23 (P3). This stub is sufficient for P2 agent frontmatter
references to resolve.

Outline:
- 6-axis review checklist (architecture alignment / pattern correctness / test
  sufficiency / security smells / perf smells / dead-code drift).
- OOP/SOLID violation catalog with code-smell examples.
- Cyclomatic + cognitive complexity heuristics.
- Common design-pattern misuse patterns.
- `gh` CLI cookbook (pr view, run list, run view --log).
- Output template: Executive Summary, Findings (with badge), Test sufficiency,
  CI status, Recommendation (approve / request-changes / comment).
