# audit — shipped (v0.1.30)

This workflow is a real fragment+gate body (`features/lifecycle/workflows/audit.py`,
shipped v0.1.30 / T-30-E-01). It scopes an audit, scans for drift, and triages findings
into dispositions; its steps communicate through the run-scoped workflow-step handoff
ledger (v0.1.30 Item 5). The terminal Python gate is disposition-only — it advances no
release phase and **deletes nothing** (audit output is disposition-ready: status tokens
and routing, never a destructive change).

The fragment files in this directory are the per-step prompt bodies. The authoritative
step sequence lives in the workflow body module (`_SEQUENCE` in `audit.py`); it is not
duplicated here, to avoid drift.
