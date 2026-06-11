---
name: release-closure-leaves-consumed-backlog-unsanitized
status: Open
severity: HIGH
session_id: sess_8adf5659
reported: 2026-06-10
surface: release CLOSURE protocol (dadaia-release-closure skill) + specs doctor
---

**Symptom:** Backlog items that were picked, consumed into a release, implemented,
shipped, and archived remain in `specs/backlog/` with stale `Status: OPEN`,
`Status: PICKED`, or `Status: CANDIDATE` markers. A 2026-06-10 sweep found **9+
backlog files whose content was fully delivered by archived releases** but whose
status still presents them as actionable:

| Backlog file | Actually delivered by | Stale status |
|---|---|---|
| `specs-evolution-migration-framework.md` | v0.1.6 (WS-SPECS-EVOLUTION S01–S06, `dadaia specs upgrade`) | OPEN |
| `full-codex-compatibility.md` | v0.1.6 (FEAT-CODEX-COMPAT-100) + v0.2.2 residuals | OPEN |
| `codex-context-hook-and-workflow-enforcement-hotfix.md` | v0.1.6 FR-C04 + v0.1.7 ctx-inject determinism | OPEN |
| `review-gate-enforcement-decision.md` | v0.1.6 FR-L02 / T-016-L04 (FORK-1 resolved → option b) | PICKED — "blocked on operator grill" (the grill already happened) |
| `session-orchestration-semaphore.md` | superseded by state-model redesign, delivered v0.1.6/v0.2.0 | PICKED |
| `software-architect-anti-slop-specialization.md` | v0.1.6 T-016-A08 | PICKED |
| `cross-platform-os-compatibility.md` (+ ledger) | v0.1.8 rc-1 + rc-2 | CANDIDATE |
| `v0.2.0-agentic-lifecycle.md`, `v0.2.0-soul-and-correctness-fold.md`, `v0.2.1-vision-fidelity-fold.md` | v0.2.0 / v0.2.1 (closed + archived) | PICKED |

Additionally, resolved bug files carry non-canonical status tokens (`Fixed`,
`resolved`, `Resolved`) instead of a single canonical closed token.

**Repro:**
1. `grep -ri "Status:" specs/backlog/*.md` — observe OPEN/PICKED/CANDIDATE markers.
2. Compare against `specs/_archive/releases/<version>/CLOSURE.md` for the releases
   listed above — each documents the corresponding workstream as accepted/DONE.
3. `dadaia specs doctor` — exits without flagging any of these stale entries.

**Expected:** The product lifecycle contract is:
`backlog / bugs → release → memory updated + release archived + bug resolved +
backlog entry marked DELIVERED/CONSUMED`.
The CLOSURE phase (dadaia-release-closure protocol, executed by product-engineer)
must include a mandatory **disposition sweep**: every backlog item and bug picked
into (or superseded by) the release gets its status flipped to a terminal token
(`DELIVERED — vX.Y.Z` / `SUPERSEDED — <slug>` / `Closed`) with an evidence pointer,
per release-governance (never delete, always mark with reason). `specs doctor`
should gain an invariant that flags backlog entries whose status is
OPEN/PICKED/CANDIDATE but which are referenced as consumed/accepted by an archived
release CLOSURE, and bug files with non-canonical status tokens.

**Notes:** Found on the self-hosting source workspace, 2026-06-10. The stale
entries actively mislead release planning: a PM/PE reading the backlog would
re-pick already-shipped work (e.g. cross-platform-os-compatibility presents a
~46 KB CANDIDATE spec that v0.1.8 already implemented). One-time data cleanup of
the 9 stale entries is being performed by hand (PM curation); this bug tracks the
missing **mechanism** (closure-protocol step + doctor invariant) so the drift
cannot recur. No operator-local paths or secrets involved.
