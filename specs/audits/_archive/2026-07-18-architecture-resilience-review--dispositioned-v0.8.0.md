# Architecture Resilience Review — the 21-bug retrospective (2026-07-18)

> **Disposition:** v0.8.0 — all six findings (W1–W6) dispositioned; see
> **[Disposition — release v0.8.0](#disposition--release-v080)** at the end of this file.
> Everything between this line and that section is the original 2026-07-18 record,
> unaltered.

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

---

## Disposition — release v0.8.0

**Disposing release:** v0.8.0 (`specs/_archive/releases/v0.8.0/`) — audit-disposition
release of the 2026-08-14 grill.
**Dispositioned:** 2026-08-14 · **Author:** product-engineer.
**Basis:** operator grill of 2026-08-14, ADR #2
(`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T130830Z-refine-specs.html`),
over the verification of
`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T041500Z-deep-triage.html`
against HEAD `8a8f4f80`.

**Unit of disposition.** This audit's findings are **W1–W6** — the five structural
weaknesses of §2 plus W6. The 25-row dataset of §1 is the *evidence* that produced those
weaknesses, not a list of findings, and is therefore not dispositioned row by row; each of
those defects was already closed by its own bug ledger stream at the time of the review.
The four requests of §4 map onto this table: the proposed `workflow-engine-unification`
onto **W4**, the proposed `normalize_zone()` onto **W5**, the proposed thin-wrapper
projected scripts onto **W6**, and "everything in W1–W3 is DONE" onto **W1–W3**.

**The audited object no longer exists.** This review is entirely about the lifecycle
workflow engine — its workers, gates, fragments, `run_store.py`, `AgentRunResult`,
`domain_payload`, the durable ledger payload and the three parallel engines. Release
v0.3.0 demolished all of it: "the engine core, its four workflow bodies, the
`dadaia lifecycle` verb group, the Layer-2 worker adapters, the panel Workflows and
Model-policy tabs, the fragment and persona asset trees, the workflow schemas, the
container wiring, the import-linter contracts and every line of prose that described them
are gone" (`specs/_archive/releases/v0.3.0/CLOSURE.md:10-17`; 348 files, +1 775 / −61 883,
net **−60 108** at `:38`). Independent check at HEAD: `run_store|refuse_completed_rerun|
AgentRunResult|domain_payload|emit_progress|fragment_gate|WorkflowEngine` returns **zero
matches in production code** — every hit is historical text under `specs/`. The law
ratified the outcome: "Arm A is agent-dispatched, not engine-run … No workflow engine
assembles prompts or advances gates on your behalf" (§1).

| # | Finding | Audit's own status | Disposition | Evidence |
|---|---------|--------------------|-------------|----------|
| W1 | Implicit worker↔gate contract | "Now enforced" | `rejected` — moot by removal | Declared DONE by the audit itself (§4, last bullet); the workers and the three-envelope translation it governed were deleted in v0.3.0. Nothing left to enforce or to fix |
| W2 | Model steps held state-mutation power | "Now enforced" | `rejected` — moot by removal | DONE at review time, object removed afterwards. The surviving sentence — "workers produce artifacts; Python produces effects" — is an architecture principle carried in memory, not an open item |
| W3 | Gates validated reports, not reality | "Now enforced" | `rejected` — moot by removal | DONE at review time, object removed afterwards. The living equivalent is the diff-based push gate (`features/chokepoints/service.py:309`), which validates the real pushed sha |
| W4 | Three parallel engines → proposed `workflow-engine-unification` | "Remaining (proposed, next release) — the single highest-leverage simplification left" | `rejected` — superseded by demolition | The three engines were not unified, they were deleted (`specs/_archive/releases/v0.3.0/CLOSURE.md:10-17`, net −60 108 lines at `:38`, ≈ −25 419 LOC of production code). The delivered simplification is strictly larger than the proposed one; the proposal has no object |
| W5 | No canonical path convention → proposed `normalize_zone()` | "Remaining (proposed)" | `rejected` — premise dead | The "zone" concept (an engine-side TASKS write-set) no longer exists: `normalize_zone|write_scope` under `dadaia_workspace/` → 0 matches; the only surviving `zone` is the unrelated `HygieneZone` (`core/models/hygiene.py:72`) |
| W6 | Projected assets duplicate package logic → proposed thin wrappers | "Remaining (proposed)" | `superseded` by `specs/backlog/thin-wrapper-projected-scripts.md` | The **sole surviving concern**: the projected scripts outlived the demolition. `dadaia_workspace/public/scripts/lint-memory-atoms.py` is still a standalone re-implementation (own heading allowlist, own schema validation), and `features/specs/catalog.py:317-320` admits it "Mirrors `generate-memory-catalog.py:generate_index_md`". The direction is today **inverted** relative to the proposal — the package shells out to the script (`features/specs/doctor_memory.py:38-40,357`) rather than the script delegating inward. Extracted as a backlog entry written against HEAD with the corrected direction (grill ADR #2), so rejecting this audit does not lose it |

**Score:** 5 `rejected` · 1 `superseded` — 6 of 6 dispositioned, none dropped (law §5).

**Archive:** this file moves to
`specs/audits/_archive/2026-07-18-architecture-resilience-review--dispositioned-v0.8.0.md`
in release v0.8.0. Everything above this section is the original record, unaltered.
