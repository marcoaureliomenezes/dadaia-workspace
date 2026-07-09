---
release: v0.1.72
phase: IMPLEMENTATION
---

# Active release: v0.1.72 — Gate coherence: repair paths + preflight enforcement

Remediation of 6 bugs reported from the operator's remote against `c33a07aa` (round 3 —
all in/around the v0.1.69 preflight subsystem). The architectural failure: **gates
shipped without repair paths, and an advisory gate the workflow verbs never enforced.**
The consumer (dd-chain-capture v0.2.0, IMPLEMENTATION) was fully deadlocked: preflight
blocked on stale memory the rules forbade repairing, then would block on the workspace's
own lease and its own protected evidence — while the verbs it guards ran anyway.

- FR1 (CRITICAL) `memory-agent-tier-migration-deadlock` — `specs upgrade` step
  `agent-tier-frontmatter` (v2→3): the missing migration for the v0.1.61 schema-drop.
- FR2 (HIGH) `rebind-does-not-adopt-same-process-lease` — pid-lineage discrimination:
  bind adopts a same-lineage lease; the preflight probe never calls our own process
  lineage a "live foreign holder" (aligns with acquire's rung-1 `.ptr` canon).
- FR3 (HIGH) `hygiene-preflight-blocks-protected-residuals` — block only on UNPROTECTED
  cleanup candidates (never demand deletion the cleaner itself refuses).
- FR4 (MEDIUM) `context-current-branch-stale-for-alive-repo` — `context show` reports
  the live checked-out branch for ALIVE repos (+ `stored_branch` restore metadata).
- FR5 (HIGH) `fake-pipeline-blocks-missing-artifact-evidence` — the pipeline verb gets
  the driving fake (artifact evidence + APPROVED) release-definition/implement-review had.
- FR6 (HIGH) `workflow-verbs-run-despite-blocked-preflight` — pipeline/implement-review
  enforce the preflight gate before creating a run; `--skip-preflight` is the explicit
  visible override.

Acceptance gate: the full workflow chain replayed on the operator's remote against the
real dd-chain-capture v0.2.0 (upgrade → bind-adopt → preflight PASS → fake pipeline
completes → verbs refuse when preflight blocks).
