# research — shipped (v0.1.30)

This workflow is a real fragment+gate body (`features/lifecycle/workflows/research.py`,
shipped v0.1.30 / T-30-E-02). It scopes research questions, runs a bounded
investigation, and synthesizes a recommendation; its steps communicate through the
run-scoped workflow-step handoff ledger (v0.1.30 Item 5). Synthesis output points to a
recommended backlog or release action.

The fragment files in this directory are the per-step prompt bodies. The authoritative
step sequence lives in the workflow body module (`_SEQUENCE` in `research.py`); it is not
duplicated here, to avoid drift.
