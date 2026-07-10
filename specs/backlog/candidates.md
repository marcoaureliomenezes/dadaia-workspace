# Backlog index — PM-curated

> Rebuilt 2026-07-09 (v0.1.73 FR2); **release-planned 2026-07-09** (operator goal: full
> review → user-impact prioritization → 5 releases absorbing the ENTIRE backlog).
> Every entry re-verified still-open against HEAD `7b08beef` on 2026-07-09 (grep evidence
> per entry: tier fallback present in `reader.py:173`, `sys.platform` TODOs present,
> no partial-archive invariant in `doctor_release.py`, `write_scope_from_tasks` wired in
> `pipeline` only, **seven** — not six — preflight block sites with null
> `operator_command` including `required handoff gate failed`, traversal tokens still
> pass `_extract_globs`).

## User-impact classification

| Impact class | Entries | What the operator gains |
|---|---|---|
| P1 — daily-loop speed & trust | `test-suite-remediation-waves` | every push stops paying ~13 min of serial suite; 1,000–1,200 tests that each mean something |
| P2 — workflow operability | `central-bind-resolution-seam`, `preflight-block-reasons-missing-operator-command`, `implement-review-write-scope-from-tasks-parity` | the #1 recurring pain class (F2: 8 reports) fixed at the seam; every preflight block tells you the exact command; no under-scoped workers on any verb |
| P3 — visible UX (ratified) | `panel-tab-reorg-agentic-layers` | the panel names the two agentic layers the operator actually governs |
| P4 — invisible robustness | `tasks-write-scope-traversal-hardening`, `specs-doctor-partial-archive-invariant` | parser can never silently widen scope; doctor flags residue-masquerading-as-archive |
| P5 — date-gated cleanup | `dispatch-band-legacy-fallback-removal` (≥ 2026-08-01), `platform-seam-todo-retirement` | one platform-gate idiom; deprecation windows honored, debt actually dies |

## The 5 releases (entire backlog absorbed — nothing remains unassigned)

| Release | Entries | Scope one-liner | Sequencing rationale |
|---|---|---|---|
| **v0.1.75 — test-suite rearchitecture** | `20260709-test-suite-remediation-waves` | ~4,450 → ~1,155 fns per the 7 per-cluster classification plans (`.dadaia/tmp/claude/20260709/test-rearch/`); pre-push `--quick`, pytest-xdist on unit tiers, `tests/tmp/` gitignored, shared session-scoped fixtures | FIRST: every later release pays the suite tax twice per push; plans are fresh; operator-mandated |
| **v0.1.76 — lifecycle operability** | `20260709-central-bind-resolution-seam`, `20260709-preflight-block-reasons-missing-operator-command`, `20260709-implement-review-write-scope-from-tasks-parity` | single bind-resolution seam + parametrized all-verbs contract test; **7** preflight block sites gain exact `operator_command`; `implement-review` gains `write_scope_from_tasks` + `--write-scope` parity | Highest operator pain after tests; the three share the lifecycle/CLI surface — one review pass |
| **v0.1.77 — panel agentic-layers reorg** | `20260708-panel-tab-reorg-agentic-layers` | 7→6 primary tabs: Projects \| 1º Agentic Layer (Sub-agents + merged Sessions dashboard) \| 2º Agentic Layer \| Reports \| Academy \| Servers; CSP hash recompute; API surfaces unchanged | Rides the v0.1.75-consolidated panel test architecture (golden/API-contract + Playwright) — DOM-contract churn is cheap now |
| **v0.1.78 — gate & doctor hardening** | `20260709-tasks-write-scope-traversal-hardening`, `20260707-specs-doctor-partial-archive-invariant` | `_extract_globs` rejects absolute/`..`/`~`/`$` tokens (defense-in-depth); WARNING invariant for artifact-empty `_archive/releases/<id>/` dirs honoring SPEC-DOC-027 allowlist + segmented layouts | Small, disjoint, both LOW — one tight release; keeps v0.1.76 from widening |
| **v0.1.79 — deprecation strips & platform seam** | `20260707-dispatch-band-legacy-fallback-removal`, `20260707-platform-seam-todo-retirement` | strip `tier:` fallback + `MissingTierError` alias (flip AC-6 test to unknown-key truth); replace 3 in-body `sys.platform` checks with `PLATFORM.has_fcntl` | **Constraint: ship on/after 2026-08-01** (dispatch-band re-projection window). Locking-adjacent work benefits from the rearchitected, stable no-steal suite; frozen-suite zero-diff gate applies |

Per `release-governance`: each release still runs its own mandatory grill before SPEC;
this plan fixes the pick and the sequence, not the SPECs. Bugs outrank this plan if new
ones open (open-work-outranks-backlog law). Ledger at planning time: **0 open**.

## Grill verdict (2026-07-09, software-architect — plan APPROVED with edits, all applied)

Sequencing upheld: 75 → 76 → 77 → 78 → 79 (no resequence justified). Binding
cross-release obligations recorded here:

1. **[CRITICAL] v0.1.75 owns the frozen-suite re-baseline explicitly.** The spec_context
   consolidation (183→61) merges files of the frozen v0.1.50 no-steal suite — neither a
   sibling addition nor a symbol-forced repoint, i.e. a re-baseline. The v0.1.75 SPEC
   carries an FR: QA-ship-gate-adjudicated re-baseline defining the SUCCESSOR frozen
   baseline (surviving param decision tables + verbatim concurrency/property files).
   v0.1.79's platform-seam "frozen suite zero-diff" acceptance is restated against that
   successor baseline.
2. **v0.1.75 coordination:** leave the bind-resolution integration cluster
   (`test_cli_bound_session_resolution`, `test_codex_thread_id_bind`,
   `test_context_show_reflects_bind`) minimally merged — v0.1.76 rewrites it into the
   all-verbs contract test. Panel consolidation single-sources the tab list in one
   fixture so v0.1.77 is a one-list change.
3. **v0.1.76 grill corrections applied to the entries:** SEVEN null-`operator_command`
   sites (incl. `required handoff gate failed`, service.py:416); a partial seam already
   exists (`cli/_specs_resolution.py`) — the gap is `context show` + ~12 lifecycle verbs
   with hardcoded `--context "dadaia-workspace"` defaults (user-visible CLI change);
   contract test must use dynamic Typer-walk enumeration + import-boundary lint, not a
   static list.
4. **v0.1.75 FR-speed is wiring-only:** `checks_for` already takes `quick` — the change
   is `pre-push-ci-gate.sh:103` + xdist deps, not engine work.

## Entry index

| Entry | Priority | Release | One-liner |
|---|---|---|---|
| `20260709-test-suite-remediation-waves` | HIGH (operator mandate) | v0.1.75 | Rearchitect to 1,000–1,200 high-value tests |
| `20260709-central-bind-resolution-seam` | HIGH | v0.1.76 | Fix the bind-visibility contract ONCE (F2: 8 reports, 5 partial fixes) |
| `20260709-preflight-block-reasons-missing-operator-command` | MEDIUM | v0.1.76 | 7 preflight block reasons carry no operator_command |
| `20260709-implement-review-write-scope-from-tasks-parity` | MEDIUM | v0.1.76 | implement-review derives no TASKS.md write scope (only pipeline does) |
| `20260708-panel-tab-reorg-agentic-layers` | LOW-MED | v0.1.77 | Operator-ratified panel tab reorg (Agentic Layer grouping) |
| `20260709-tasks-write-scope-traversal-hardening` | LOW | v0.1.78 | Reject `/`-absolute, `..`, `~`, `$` in derived write-set globs |
| `20260707-specs-doctor-partial-archive-invariant` | LOW | v0.1.78 | WARN invariant for artifact-empty archived release dirs |
| `20260707-dispatch-band-legacy-fallback-removal` | LOW | v0.1.79 | Dated strip — executable from 2026-08-01 |
| `20260707-platform-seam-todo-retirement` | LOW | v0.1.79 | Replace 3 `sys.platform` TODOs with the PLATFORM seam |

Archived: `_archive/20260704-fast-tier-persona-validation.md` (terminal REJECTED in
v0.1.64 — the recorded override path travels with the file).
