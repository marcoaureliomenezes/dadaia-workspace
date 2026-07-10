---
name: platform-seam-todo-retirement
status: superseded
superseded_by: lock-lease-session-identity-kernel (consolidation 2026-07-10)
opened: 2026-07-07
owner: project-manager (curates)
source: "v0.1.61 closure backlog return (audit A-3 deferral — grill correction: the audit's cited anchor `features-import-infrastructure-direct-debt` was consumed at R6/v0.1.54, so this NEW tracked return replaces it)"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/locking.py#_default_workspace_lock" }
    change: "retire the aged PLATFORM.has_fcntl TODOs: replace the in-body sys.platform == 'win32' checks in the lazy lock-adapter factories (_default_workspace_lock + _default_context_lock) with the PLATFORM.has_fcntl capability flag (the container's sole authorized platform gate, per container.py:165-177). The TODOs date to T-018-05 ('once PLATFORM is stable') and PLATFORM has long been stable. CAUTION: this surface is directly adjacent to the frozen v0.1.50 no-steal suite (lease/locking paths) — the change must land with the frozen suite proven zero-diff and any symbol-forced repoint adjudicated at the QA ship gate, per the quality-assurance.md frozen-suite invariant law."
  - subject: { kind: code, ref: "dadaia_workspace/features/telemetry/service.py#_default_refresh_lock" }
    change: "same retirement for the telemetry lazy adapter factory: replace the in-body sys.platform check ('TODO: Replace with PLATFORM.has_fcntl once WS-1 lands') with PLATFORM.has_fcntl. Lower-risk than the locking.py pair (telemetry refresh lock, not the lease path) but ships in the same pass for one consistent platform-gate idiom."
---

# BACKLOG — Retire the aged `PLATFORM.has_fcntl` TODOs (platform-seam consolidation)

**Priority:** LOW. Three lazy adapter factories still gate POSIX-vs-Windows adapter selection
with in-body `sys.platform == "win32"` checks carrying stale TODOs ("replace with
`PLATFORM.has_fcntl` once stable" — it has been stable for many releases):
`features/spec_context/locking.py#_default_workspace_lock` / `#_default_context_lock` and
`features/telemetry/service.py#_default_refresh_lock`. `container.py` already reads
`PLATFORM.has_fcntl` as "the sole authorized platform capability flag" — these factories are
the residue of the pre-container transitional pattern (ADR-1 lazy imports).

**Why deferred from v0.1.61 (audit A-3):** the `locking.py` pair sits directly adjacent to the
**frozen v0.1.50 no-steal suite** — touching lease/locking selection inside an audit-remediation
release was adjudicated risk ≫ value. The v0.1.61 grill also corrected the audit's tracking
claim: the cited backlog anchor `features-import-infrastructure-direct-debt` was **consumed at
R6/v0.1.54** and no longer exists — this entry is the new tracked return.

**Acceptance sketch:** zero `sys.platform` reads outside `core/platform.py` in the three
factories; behavior identical per platform; **frozen no-steal suite zero-diff** (or a
symbol-forced repoint adjudicated at the QA ship gate, never silently re-baselined).

**Anchor:** `features/spec_context/locking.py#_default_workspace_lock` (+
`_default_context_lock`) and `features/telemetry/service.py#_default_refresh_lock`.
