---
name: precommit-backlog-doctor-blocks-unrelated-commits
status: Open
severity: MEDIUM
reported: 2026-06-30
surface: pre-commit hook (backlog doctor / BL-SCHEMA gate)
session_id: null
---

**Symptom:** The pre-commit hook runs `backlog doctor` and blocks the commit on
pre-existing BL-SCHEMA errors in backlog items that are **not part of the changeset**.
A commit whose staged paths are entirely outside `specs/backlog/` (here: only
`dadaia_workspace/public/personas/**`, `dadaia_workspace/public/lifecycle_fragments/**`,
and `specs/releases/v0.1.44/TASKS.md`) is still rejected, so unrelated in-scope
release-implementation work cannot land until the backlog is repaired.

Two pre-existing errors trigger the block:

```
[pre-commit] BLOCKED: backlog doctor found 2 error(s):
  BL-SCHEMA [specs-truth-realignment-constitution-memory] subject ref
    'memory/quality-assurance.md#layer-schema' (kind=doc) resolves to no known anchor;
    add it as an alias in the operator alias map, or correct the ref.
  BL-SCHEMA [workflow-model-governance-operator-profiles-and-context-overlays] subject ref
    'dadaia_workspace/core/protocols/workflow_model_policy_store.py#WorkflowModelPolicyOverlay'
    (kind=code) resolves to no known anchor; add it as an alias in the operator alias map,
    or correct the ref.
```

**Repro:**
1. Have two backlog items with subject refs that resolve to no known anchor (state above).
2. Stage a change that touches no file under `specs/backlog/` (e.g. edit a file under
   `dadaia_workspace/public/personas/`).
3. `git commit` → blocked by backlog doctor, despite the changeset not touching backlog.

**Expected:** The pre-commit backlog-doctor gate should scope its enforcement to commits
that actually modify `specs/backlog/**` (or otherwise not couple unrelated commits to the
global backlog health). A commit that touches zero backlog files should not be blocked by
pre-existing backlog inconsistency. Pre-existing backlog defects are real and should be
fixed by `project-manager`, but they should not freeze every other agent's commits.

**Notes:** Observed while implementing v0.1.44 tasks T-44-2 (persona atoms) and T-44-7
(fragment role reassignment) — both purely AI-entity-surface text changes. The lease line
also logged `WARN ... records a dead holder pid ... with a fresh heartbeat ... allowing
(advisory degradation, DP-4 zero-false-block)`, which is the relaunched-incumbent path and
did not itself block. Only the backlog-doctor stage blocked. The two flagged backlog items
pre-date this release and are outside the ai-engineer scope (backlog curation is
`project-manager` per the `backlog-ownership` rule).
