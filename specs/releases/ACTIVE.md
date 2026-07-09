---
release: none
phase: none
---

# Active release: none

**v0.1.72 SHIPPED + CLOSED (PR #139 `6b517d79`).** Round-3 remediation: 6 remote bugs
(1 CRITICAL) fixed at root cause — gate coherence: every gate ships its repair path
(agent-tier migration v2→3, lease lineage adoption, protected-residual exemption, live
branch) and the preflight the CLI reports is the preflight pipeline/implement-review
enforce (--skip-preflight explicit override). Validated by full-chain replay on the
operator's remote against live dd-chain-capture v0.2.0.

Recurrence audit (150 bugs): ~40% of the v0.1.66–71 arc's resolutions were need-unmet
(median re-report <11h) — resolution law now in quality-assurance.md. Ledger: 4 open,
all scoped to the NEXT release (governance-hygiene): bugs-store single append-only JSONL
+ _archive consolidation (operator contract), backlog timestamp prefixes + cleanup,
agent-tier ReDoS, specs_bkp-trips-dirty-gate, F2 central bind-resolution seam.
