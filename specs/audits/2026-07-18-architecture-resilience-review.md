# Architecture Resilience Review — the 21-bug retrospective (2026-07-18)

**Mandate (operator):** the Consumer validation cycle surfaced ~21 defects one after
another. That pattern is architectural, not incidental. This review classifies every
defect of the cycle by systemic root cause, names the structural weaknesses, states
which laws are now enforced in code, and proposes the remaining simplifications.
Law going forward: **simplicity and resilience** — model workers produce artifacts;
Python owns truth, effects, and transactions.

## 1. The dataset — every defect of the cycle, classified

| # | Bug | Systemic root cause |
|---|-----|---------------------|
| 1 | fake-backlog-definition-cannot-complete-user-flow | A. Tests that don't test |
| 2 | certification-passes-without-complete-workflow-chain | A |
| 3 | certify-cannot-install-installed-provider | B. External-state dependency |
| 4 | init-succeeds-after-provider-bootstrap-failure | B |
| 5 | codex-live-workflow (bare "completed" payload) | C. Trusted worker self-report |
| 6 | backlog-author-missing-canonical-subject-input | D. Implicit worker contract |
| 7 | audit-fragment-schema-envelope-mismatch | D (three envelope translations) |
| 8 | backlog-author-bare-payload-breaks-release-handoff | C |
| 9 | live-release-definition-rejects-fresh-context | D (no greenfield contract) |
| 10 | projected-pre-gate-silent-allow | F. Unobservable contracts |
| 11 | release-commit-gate-ignores-existing-plan-review-payload | E. Non-transactional state |
| 12 | release-plan-author-does-not-converge-validation-contract | D (presentation vs semantics) |
| 13 | release-definition-completes-without-persisting-artifacts | C |
| 14 | closure-catalog-references-missing-memory-atom | E (derived state hand-edited) |
| 15 | implementation-review-approves-unexecuted-validation | C |
| 16 | closure-breaks-canonical-backlog-anchor | E (regeneration destroyed truth) |
| 17 | completed-workflow-rerun-not-refused | G. Divergent engines |
| 18 | implementation-reviews-resume-token-without-cli-resume | G |
| 19 | lifecycle-workflows-leave-python-bytecode-in-repo | E |
| 20 | closure-allows-memory-doctor-warnings / atom-without-heading/frontmatter | C + D |
| 21 | implementation-write-scope-omits-entrypoint / zone-misses-context-repo / worker-at-root | H. Ambiguous path convention |
| 22 | release-definition-codex-hangs (perceived) / backlog progress missing accepted | F |
| 23 | implementation-closure-leaves-uncommitted-release-tree | E |
| 24 | projected-memory-linter-cannot-find-schema | I. Duplicated projections |
| 25 | lifecycle-accepts-noncanonical-release-id → invalid memory slug | H |

## 2. The five structural weaknesses (why bugs kept coming)

**W1 — The worker↔gate contract was implicit.** Prompts asked for one shape, gates
validated another, and a payload crossed three envelopes (AgentRunResult →
domain_payload → durable ledger payload). Every translation layer was a defect
factory (bugs 5–9, 12, 20). *Now enforced:* one-envelope merge (top-level domain
fields always retained), literal copyable templates in fragments (atom, PLAN table,
entrypoint forms), and the canonical anchor set handed to authors.

**W2 — Model steps held state-mutation power.** ACTIVE.md, catalog.json, memory,
git state were writable by workers; a blocked step left half-mutated governance
state (bugs 11, 14, 16, 19, 23, and the whole closure family). *Now enforced — the
core law of this review:* **workers produce artifacts; Python produces effects.**
Closure is transactional (snapshot/rollback on block); post-success effects (ACTIVE
reset, catalog regeneration from atoms, cache sweep, repo commit) are deterministic
Python; derived files can never be hand-edited into incoherence because they are
regenerated.

**W3 — Gates validated reports, not reality.** A step could "pass" on its transport
envelope while the deliverable did not exist (bugs 1, 2, 5, 8, 13, 15). *Now
enforced:* disk-truth gates everywhere — per-file deliverable requirements on every
create step, disk-diffed evidence enrichment, executed-test close gate, memory
lint+heading gate, persisted-payload reconciliation at the terminal gate.

**W4 — Three parallel engines with near-identical semantics.** Pipeline,
fragment-gate, and backlog each reimplemented run/resume/rerun/progress/ledger;
every fix had to land three times and rounds 9–15 were largely the SAME class
resurfacing in a sibling engine (bugs 17, 18, 22). *Partially mitigated:* shared
guards (`refuse_completed_rerun`, `emit_progress`) now live once in `run_store.py`.
*Remaining (proposed, next release):* fold the three engines into ONE
`WorkflowEngine` with per-workflow step tables — this is the single highest-leverage
simplification left, and it is a deliberate refactor release, not a hotfix.

**W5 — No canonical path convention.** TASKS write sets are repo-relative, workers
report workspace-relative, zones were compared verbatim (bugs 21, 25). *Now
enforced:* dual-spelling zone matching + parent-dir expansion + canonical release-id
validation at every verb entry. *Remaining (proposed):* a single `normalize_zone()`
at every path entry point instead of dual-matching at comparison sites.

**W6 — Projected assets duplicate package logic.** The standalone linter/scripts
re-implement package behavior and drift (bugs 10, 24, plus the README/CLI drift).
*Now enforced:* projected-layout schema lookup, explicit allow envelope, README
fixed. *Remaining (proposed):* projected scripts become thin wrappers that exec the
workspace venv's package code — one logic, one source.

## 3. Why this is convergence, not infinity

The defect surface moved outward monotonically: rounds 1–6 died in the fake chain
and certification; 7–11 in definition; 12–15 in closure quality; 16–18 in delivery
zones; the final rounds completed the ENTIRE cycle twice (two different games,
16/16 and 16/16 tests, playable binaries, doctor 0/0) with only peripheral findings
(final commit, a projected script's schema path). Every class that fired now has a
deterministic gate + regression test (2 747 tests, 0 failing). The recipe grew from
23 to 26 statements with full-chain, post-closure, and honest-failure assertions —
the validator can no longer be satisfied by anything less than the real user flow.

## 4. Dispositions requested by this review

- Proposed release `workflow-engine-unification` (W4) — one engine, three step
  tables; deletes ~1/3 of lifecycle code. Backlog item to be curated by PM.
- Proposed `normalize_zone()` single path canonicalizer (W5).
- Proposed thin-wrapper projected scripts (W6).
- Everything in W1–W3 is DONE and gate-enforced in this branch.
