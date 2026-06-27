# bug_report — shipped (v0.1.30)

This workflow is a real fragment+gate body (`features/lifecycle/workflows/bug_report.py`,
shipped v0.1.30 / T-30-E-03). It normalizes a reported symptom into an additive bug
record, deduplicating against existing bugs; its steps communicate through the run-scoped
workflow-step handoff ledger (v0.1.30 Item 5). The writing step is scope-locked to the
ADDITIVE `specs/bugs/**` class only (no lease, never blocked); an out-of-scope write is
gate-BLOCKED. Bug records are additive — never a destructive change.

The fragment files in this directory are the per-step prompt bodies. The authoritative
step sequence lives in the workflow body module (`_SEQUENCE` in `bug_report.py`); it is
not duplicated here, to avoid drift.
