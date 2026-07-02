# Backlog candidates

Curated index of surviving backlog items. Rebuilt 2026-07-02 after the operator-ordered
backlog sanitization + architectural deep review (post-v0.1.48; no active release).
This index lists **only** surviving open candidates — consumed, superseded, and stale
entries were removed per removal-on-release and the never-keep-the-past law.

Architecture baseline: two-layer model, Layer-1 entry harnesses `{claude, codex, pi}`,
Layer-2 = `dadaia lifecycle` Python workflow bodies driving pi/codex workers.

**Open-bug debt (outranks plain backlog at pick):** none — the last open bug
(`bugs-append-bound-session-falls-through-to-cwd-specs`) was resolved by R2/v0.1.50.

---

## Release sequence (grilled 2026-07-02)

Operator-approved conversion order — every surviving entry and every open bug placed
exactly once. Grill decisions: (1) the backlog becomes git-tracked repository truth
(R1); (2) panel plumbing runs EARLY (R4); (3) panel-ux precedes plugin packs — the
recorded `plugin-scope` deviation stands. Suggested ids v0.1.49–v0.1.60; actual ids
are assigned at each `release define`, and each release still runs its own mandatory
grill on the picked set before SPEC.

| # | Release theme | Consumes (backlog / bugs) | Why this position |
|---|---|---|---|
| R1 | **SHIPPED — v0.1.49** (merged `3743cb06`, PR #87, 2026-07-02) | bugs `backlog-gitignored-governance-vacuous` + `backlog-subject-registry-invariant-content-scan`; `memory-heading-allowlist-extension` (all consumed) | Fix the release machine first: git-tracked backlog makes the BL-* chokepoint/CI real; fail-closed registry stops docstring/test junk anchors. |
| R2 | **SHIPPED — v0.1.50** (merged `7b198d49`, PR #89, 2026-07-02) | `lease-kernel-identity-hardening`; `context-dead-exit-path`; bug `bugs-append-bound-session-falls-through-to-cwd-specs` (all consumed/resolved) | The single deterministic lock, session attribution, and the context exit path are the safety spine; removes the reproduced self-block pain. |
| R3 | **SHIPPED — v0.1.51** (merged `5329cd96`, PR #91, 2026-07-02) | `e2e-journey-coverage-and-test-canon` (consumed) | Safety net BEFORE the refactor chain; the master lifecycle E2E can only assert correct bind attribution after R2. Residue-test disposition aligns the suite with the no-slop law. |
| R4 | Panel plumbing | `panel-sessions-cost-dashboard-only` → `panel-runtime-reliability` | Operator-elected, fully independent; kills the SQLite corruption bug; reliability lands on the post-removal route surface; every later release runs a smaller suite. |
| R5 | Legacy purge | `legacy-surface-retirement`; `hygiene-and-dead-code-cleanup`; `centralize-release-semver-canon`; `telemetry-tier2-chmod-unguarded-on-windows` | Delete before refactoring: shrinks the surface R6–R9 must restructure and the import contracts must cover. |
| R6 | Import boundaries | `import-boundary-enforcement`; `features-import-infrastructure-direct-debt`; `pid-probe-seam-consolidation` | Contracts green + CI-wired + `workflows ↔ lifecycle` cycle broken; silent erosion stops here so all later structure lands under enforcement. |
| R7 | Architecture decomposition | `architecture-uml-decomposition` | SpecsDoctor/api.py splits + reports_* merge land under the now-enforced contracts; ships the committed UML assets. |
| R8 | Lifecycle verb governance | `lifecycle-verb-governance-uniformity` | Settles the runtime/policy seam (resolver on EVERY verb, loop through the runner gate, TRANSITIONS reconciliation) before prompt assembly is rebuilt. |
| R9 | Injection canon | `context-injection-role-phase-canon`; `fragment-workflow-base-dedup` | The dedup base creates the ONE prompt-assembly seam; the role→atom map + phase threading are implemented at that seam in the same release — five bodies touched once, not twice. |
| R10 | Harness & projection distribution | `harness-isolation-profiles`; `consumer-agents-md-fanout-redesign` | `init --harness` profiles + typed harness registry + consumer AGENTS.md fan-out redesign — the projection/install machinery, matured after the structural chain. |
| R11 | Panel UX overhaul | `panel-ux-overhaul` | Visual redesign on the stabilized post-R4 panel, under the recorded `plugin-scope` deviation (operator 2026-07-02). |
| R12 | Capability tail | `plugin-packs-and-install-command`; `model-tier-efficiency-and-fast-tier-utilization` | Pure new capability, zero debt: packs + install command, then Layer-1 fast-tier assignments. |

---

## HIGH

### `import-boundary-enforcement` — Import-boundary enforcement
Red import-linter chains fixed + CI wiring + features-no-cross-feature contract +
`workflows ↔ lifecycle` cycle break (shared governed-catalog seam) + core-purity follow-up.

### `lease-kernel-identity-hardening` — Lease-kernel identity hardening
Self-block root fix (pid self-recognition), pid-veto preservation on unreadable
ACTIVE.md, SPEC-DOC-029 namespace-aware coherence, by-session index hygiene.

### `lifecycle-verb-governance-uniformity` — Lifecycle verb governance uniformity
Policy resolver on EVERY verb; audit/research/bug_report invocability decision;
implement/review loop fixes (rejection digest, runner gate, CLI caller); TRANSITIONS
table reconciliation (absorbed the retired `review-rejection-rework-path` idea).

### `architecture-uml-decomposition` — Architecture UML decomposition *(2026-07-02)*
Split the SpecsDoctor god class (2,820 lines / 54 methods) and panel views/api.py
(1,402 lines / 24 functions); merge the reports_* feature triplet; commit canonical UML
assets under `specs/assets/architecture/`.

### `legacy-surface-retirement` — Legacy surface retirement *(2026-07-02)*
Delete legacy `bug new` Markdown path, overdue-deprecated `server dashboard`, inert
`features/orchestration` stubs, never-raised backtrack exceptions; audit
`features/migrate` for still-required consumer upgrade steps.

### `context-injection-role-phase-canon` — Context-injection role/phase canon *(2026-07-02)*
Role→memory-atom default map (architect→architecture.md, qa→quality-assurance.md; fix
`implementation.qa_review` missing `quality_assurance_atom`); phase threading into
Layer-2 context selection; fragment/persona coherence doctor; Layer-1 self-pull vs
injected-digest decision (grill mandatory).

### `e2e-journey-coverage-and-test-canon` — E2E journey coverage + test canon *(2026-07-02)*
Master spec-context lifecycle E2E (create→alive→bind→inject→gate in one sandbox
narrative); `specs upgrade` E2E; disposition of the post-deletion residue tests
against the written no-slop law.

### `panel-sessions-cost-dashboard-only` — Sessions: aggregated cost dashboard only *(operator-elected 2026-07-02)*
Remove the session-list table/drawer/detail route; keep the 4-card cost dashboard fed
by a server-side aggregate; prune ~1,550 lines of session-list tests incl. the stale
Playwright fixture.

---

## MEDIUM

### `panel-runtime-reliability` — Panel runtime reliability
SQLite WAL/busy factory adoption, DAO lifecycle, /api/kanban fate, mermaid-fence
decision. Owns bug `panel-telemetry-sqlite-corrupts-under-concurrent-access`.

### `panel-ux-overhaul` — Panel UX overhaul (FEAT-PANEL-UX-200)
Visual-quality + layout overhaul (tokens design system, row wrapping, theme switcher,
tab consolidation). Re-baselined 2026-07-02: Sessions surface carved out to
`panel-sessions-cost-dashboard-only`.

### `consumer-agents-md-fanout-redesign` — Consumer-repo AGENTS.md fan-out redesign
Detect Spec Context repos via spec_contexts.json; public doctor flags stale consumer
copies instead of skipping.

### `context-dead-exit-path` — context dead() exit path
Explicit refspec push + rmtree(onexc) replacement of the non-writable scan. Owns two
deferred bugs.

### `fragment-workflow-base-dedup` — Fragment workflow base dedup
Extract the shared FragmentGateWorkflow base from the 5 near-verbatim workflow bodies
(~1,500 duplicated lines) so prompt assembly has ONE seam.

### `harness-isolation-profiles` — Harness isolation profiles + harness registry
`dadaia init --harness <set>` single-harness scaffolding; central harness-identity
registry with Layer-1/Layer-2 capability typing replacing 61+ scattered string
literals (extended 2026-07-02).

### `plugin-packs-and-install-command` — Plugin packs + `dadaia plugin install`
Distribute frontend-design + devops packs; referenced by the `plugin-scope` rule.
(File recreated 2026-07-02 — the entry existed only as an index line.)

### `model-tier-efficiency-and-fast-tier-utilization` — Layer-1 model-tier efficiency (P2)
Fast-tier assignments for mechanical sub-tasks + recurring efficiency-audit trigger.

---

## LOW

### `hygiene-and-dead-code-cleanup` — Hygiene and dead-code cleanup
Audit-C dead-code inventory + agent_tier wire-or-remove + dead telemetry call sites
(incl. the unreachable panel handler fallback) + bug-path redaction sweep.

### `features-import-infrastructure-direct-debt` — features → infrastructure layering debt
Remove the 3 documented direct-import `ignore_imports` edges behind ports
(referenced by name in setup.cfg).

### `centralize-release-semver-canon` — Centralize the release SemVer canon
One shared constant in `core/specs_version.py` replacing 3 literal copies.

### `pid-probe-seam-consolidation` — Consolidate `_build_pid_probe`
One public composition-root builder instead of the hook-private de-facto seam.

### `telemetry-tier2-chmod-unguarded-on-windows` — telemetry Tier-2 chmod on Windows
Route dir/DB restriction through the FilePermissionSetter port (silent no-op today).
