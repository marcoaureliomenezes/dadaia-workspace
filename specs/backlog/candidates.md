# Backlog index — PM-curated

> **Consolidated 2026-07-10** (operator goal: full triage → eliminate stale → group by
> feature → merge the 2026-07-10 remote-user bugs → 5–6 well-described entries, lock
> bugs as P0). Result: **5 consolidated entries**. Every claim re-verified still-open
> against HEAD (post-v0.1.75 `b4de472b` line): tier fallback `reader.py:173`, 3
> `sys.platform` TODOs, no partial-archive invariant in `doctor_release.py`, panel
> still 7 tabs, seven preflight `_blocked(...)` sites defaulting
> `operator_command=None`, no traversal guards in `_extract_globs`,
> `write_scope_from_tasks` wired only at the `pipeline` verb (`lifecycle.py:1896`).
> The remote source (`z_dadaia-workspace-BUGs`) was re-checked 2026-07-10: it holds
> exactly the 5 bugs + 1 audit already intaken — nothing new outstanding.

## The 5 consolidated entries

| # | Entry | Priority | Absorbs | One-liner |
|---|---|---|---|---|
| 1 | `20260710-lock-lease-session-identity-kernel` | **P0** | CRITICAL bug `layer1-rebind-adopts-lease-to-synthetic-session-self-block` + audit `2026-07-10-lock-risk-audit-cross-harness` (all findings) + backlog `platform-seam-todo-retirement` | ONE canonical SessionIdentity + ONE liveness verdict across the lock kernel; no anon acquisition (PI); no self-block on any L1 harness; automatic deterministic release; `PLATFORM.has_fcntl` seam rides along |
| 2 | `20260709-central-bind-resolution-seam` | **P0** | recurrence family F2 (8 reports, 5 partial fixes) | ONE bind-resolution seam for every resolver-driven CLI verb + dynamic Typer-walk contract test + import-boundary lint; lifecycle `--context` hardcoded default retired (user-visible) |
| 3 | `20260710-lifecycle-pipeline-correctness-and-diagnosability` | **P1** | 4 HIGH bugs (`single-implement-verb-gated-as-review`, `full-pipeline-success-persists-running-empty-ledger`, `split-cleanup-engines-strand-stale-step-payloads`, `worker-noncompliance-block-carries-no-diagnostic-evidence`) + backlog `preflight-block-reasons`, `implement-review-write-scope-parity`, `tasks-write-scope-traversal-hardening` | the lifecycle engine tells the truth (persisted state == reported state) and every block carries evidence + the exact next command; PI `--thinking` wired; write-scope parity + parser hardening |
| 4 | `20260708-panel-tab-reorg-agentic-layers` | **P2** | — (operator-ratified 2026-07-08, stands as-is) | 7→6 primary tabs: Projects \| 1º Agentic Layer (Sub-agents + merged Sessions dashboard) \| 2º Agentic Layer \| Reports \| Academy \| Servers; CSP hash recompute; API surfaces unchanged |
| 5 | `20260710-deprecation-strips-and-doctor-cleanup` | **P3** | backlog `dispatch-band-legacy-fallback-removal` (**ship ≥ 2026-08-01**) + `specs-doctor-partial-archive-invariant` | strip the `tier:` tolerate window + `MissingTierError` alias; WARNING invariant for artifact-empty `_archive/releases/<id>/` dirs |

## Triage record (what was eliminated / adapted / merged)

- **Eliminated (stale):** `test-suite-remediation-waves` — CONSUMED by v0.1.75
  (shipped 2026-07-10, PR #145; 4,450 → 1,327 authored fns). Archived with
  `consumed_by` pointer.
- **Merged by feature (operator-ratified 2026-07-10, all four consolidation questions
  answered):** platform-seam → P0 lock kernel (same `locking.py` surface, one
  frozen-suite adjudication); preflight-reasons + implement-review-parity +
  traversal-hardening → P1 lifecycle entry (one feature family, one SPEC/review pass);
  dispatch-band strip + doctor partial-archive invariant → P3 cleanup entry.
- **Kept separate (operator decision):** the two P0s — the bind seam governs *which
  context a verb resolves*; the lock kernel governs *who holds the mutating lease* —
  distinct contracts, distinct test surfaces. Sequencing hint: lock-kernel
  SessionIdentity lands first or together.
- **Adapted:** all frozen-suite references now point at the v0.1.75 SUCCESSOR baseline
  (38-row invariant manifest), not the retired v0.1.50 file list.
- Superseded originals live in `_archive/` with `superseded_by` frontmatter
  (never-delete law). Bugs stay OPEN in `specs/bugs/bugs.jsonl` until the disposing
  release appends `resolved --resolution-evidence`; the entries above carry explicit
  disposition notes.

## Sequencing guidance (release planning input — pick still owned by PE at
release-definition per `release-governance`; open work outranks backlog)

1. **P0 first, lock kernel before/with bind seam** (#1 → #2, or one release if the
   grill deems the write surfaces disjoint enough).
2. **P1 lifecycle** (#3) next — highest operator pain after locks.
3. **P2 panel** (#4) — rides the v0.1.75-consolidated panel test architecture
   (single-sourced tab fixture makes it a one-list change).
4. **P3 cleanup** (#5) — **constraint: ship on/after 2026-08-01** (dispatch-band
   re-projection window).

Per `release-governance`: each release runs its own mandatory grill before SPEC; this
index fixes the consolidated backlog, not the SPECs. Ledger at consolidation time:
**5 open bugs** (1 CRITICAL + 4 HIGH), all absorbed into entries #1 and #3; **1 open
audit** (P0 lock risk), absorbed into #1.

## Archive

`_archive/` holds consumed/superseded/rejected entries; each carries its terminal
pointer in frontmatter. Notable: `20260704-fast-tier-persona-validation.md` (terminal
REJECTED in v0.1.64 — the recorded override path travels with the file).
