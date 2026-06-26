---
release: v0.1.26
phase: IMPLEMENTATION
segment: alpha-1
---

Active release: **v0.1.26 (R2 — `backlog_definition` workflow body +
removal-on-release hook)**. Builds on v0.1.25 R1 (canonical-subject registry +
deterministic classifier + `backlog doctor` BL-* at pre-commit/CI), which shipped
the mechanically-consistent backlog foundation. R2 implements the §4 sequenced
`backlog_definition` dadaia-workflow (intake_grill → subject_bind →
existing_backlog_review → reconcile_decision → conflict_resolution_grill →
backlog_author → backlog_review_gate), wires it behind `dadaia lifecycle backlog
define`, feeds the R1 classifier into the existing_backlog_review step, and adds
the §6 removal-on-release closure hook (consumed_backlog ledger + residual-aware
rewrite/archive). Source backlog item:
`specs/backlog/backlog-definition-workflow-dedup-conflict-control.md` (§4, §6, §8,
§9, §11-R2; all grill OQs RESOLVED). Then: `workflow-model-governance`.
