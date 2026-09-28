# TASKS — Release: 0.5.0

**Status:** Approved
**Owner:** dd-software-engineer

Paths as in PLAN (`f/` features, `i/` infrastructure, `pub/` public). Each bug = one shape-3 commit
`fix(bugs): <id> — <cause>` (code + regression test + its `BUGS.jsonl` line; loser tests and fakes
deleted in it); the task flip is its own `chore(tasks)` commit. `RED:` names the PLAN §2 row whose
`<bug-id>#<id>` statements the tests cite and which fail before the change; each write set includes its
tests. `Δ` = prod/test lines; PLAN §2.7 ceilings stop a task, never rise.

## Candidate 4 — systemic ambiguity remediation

- [x] **T-050-23..39, -42, -51, -53..56, -59..61, -63 — done.** The trace: their `chore(tasks)` and shape-3 commits, the `BUGS.jsonl` resolve records.

### W1 — stalls, loops, unclearing fixes (FR2)

- [x] **T-050-40 — Fix lines, one printer, unfixable fixes (17–19 †).** Three commits. `W:` `core/`, `hooks/`, `f/chokepoints/`, `f/spec_context/`, `cli/`
  `blocked by:` T-050-39 · `delivers:` AC2.2, AC2.3 · `RED:` PLAN §2 WP-17, WP-18, WP-19 · Δ −48/+315.
- [ ] **T-050-41 — TREE-8 alone (20).** `W:` `f/specs/` · `blocked by:` T-050-40, T-050-43, T-050-48 · `delivers:` one finding per stray path · `RED:` PLAN §2 WP-20 · Δ −115/−40.
- [x] **T-050-43 — Scripts own bug records and the seam (22, 23).** `W:` `core/`, `container.py`, `f/specs/`, `pub/skills/_shared/_privacy.py`, ledger `scripts/`, `pub/schemas/bugs/`, `i/public_assets.py`
  `blocked by:` T-050-40, T-050-70..74 · `delivers:` doctor = `bugs.py check`; seam ⇔ push · `RED:` PLAN §2 WP-22, WP-23 · Δ −700/−660.
- [ ] **T-050-44 — Backlog status and pick (24).** `W:` `f/backlog/`, backlog `scripts/`, `_release_new.py`, law · `blocked by:` T-050-43, T-050-48, T-050-58 · `delivers:` exit without hand edit · `RED:` PLAN §2 WP-24 · Δ −80/−40.
- [x] **T-050-45 — `release.py ship` (25).** `W:` `dd-release-impl/scripts/`, `f/specs/`, releases law, RC-FLOW, gitflow · `blocked by:` T-050-70..74 · `delivers:` AC2.5 · `RED:` PLAN §2 WP-25 · Δ −40/−70.
- [ ] **T-050-46 — Status line; `measured_by` (26, 27).** `W:` `core/spec_status.py`, `f/specs/`, `pub/schemas/ADRs/`, `pub/scaffold/ADRs/` · `blocked by:` T-050-40, T-050-70..74 · `delivers:` one status token · `RED:` PLAN §2 WP-26, WP-27 · Δ −20/+50.
- [ ] **T-050-47 — `specs_version.state` (28 †).** `W:` `core/specs_version.py`, `cli/commands/ci.py`, `f/{specs,migrate,workspace,chokepoints}/` · `blocked by:` T-050-40, T-050-70..74 · `delivers:` pre-push judges the pushed commit · `RED:` PLAN §2 WP-28 · Δ −34/+145.
- [x] **T-050-48 — One atom grammar (29).** `W:` navigator `scripts/`, `f/specs/`, `i/ledger_scripts.py`, `pub/scaffold/memory/` · `blocked by:` T-050-40, T-050-70..74 · `delivers:` one verdict per atom · `RED:` PLAN §2 WP-29 · Δ −155/−10.

### W2 — consolidations (FR3)

- [x] **T-050-49 — `release.py check` (30).** `W:` `f/specs/`, `core/` · `blocked by:` T-050-45, T-050-58 · `delivers:` one live release; one release-id grammar (`sa-release-id-has-three-grammars`) · `RED:` PLAN §2 WP-30 · Δ −105/−100.
- [x] **T-050-50 — Certify walks the workspace (31).** `W:` `f/{certification,reconcile}/`, recipe · `blocked by:` T-050-40, T-050-70..74 · `delivers:` AC3.2; certify children fenced (`sa-certify-children-resolve-the-live-workspace`); one finding shape (`sa-doctor-finding-has-four-shapes`) · `RED:` PLAN §2 WP-31 · Δ −126/+116.
- [ ] **T-050-52 — Subjects in the doctor (35).** `W:` backlog `scripts/`, `f/backlog/`, `core/models/backlog.py` · `blocked by:` T-050-44 · `delivers:` no circular RESOLVED · `RED:` PLAN §2 WP-35 · Δ −25/+39.

### W3 — design debt (FR4)

- [x] **T-050-57 — Work and principal branch (41, 42 †).** `W:` `f/spec_context/service.py`, `cli/commands/`, `f/specs/canon.py`, gitflow skill, repo `AGENTS.md` · `blocked by:` T-050-45 · `delivers:` AC4.2 · `RED:` PLAN §2 WP-41, WP-42 · Δ −1/+81.
- [x] **T-050-58 — Audit close; script vocabulary + atomic write (43, 48).** `W:` `f/specs/`, `i/jsonl_record_store.py`, `core/models/`, ledger `scripts/`, `registry.py` · `blocked by:` T-050-43 · `delivers:` no invalid archive, no `.tmp` leak · `RED:` PLAN §2 WP-43, WP-48 · Δ −187/−295.

### FR10 — reduction (operator-approved deletions)

Lanes: PLAN §2 FR10; files and lines: `AGGREGATE.md` §6.

- [x] **T-050-64 — L0.1 w0-infra.** `W:` `i/public_assets.py`, tests · `blocked by:` none · `delivers:` §6 W0 · Δ −35/−36.
- [x] **T-050-65 — L0.2 w0-core.** `W:` `core/`, tests · `blocked by:` none · `delivers:` §6 W0 · Δ −40/−65.
- [x] **T-050-66 — L0.3 w0-specs.** `W:` `f/{backlog,specs}/`, `cli/anchors.py`, tests; TREE-3 kept · `blocked by:` none · `delivers:` `sa-command-tree-walked-twice` · Δ −330/−391.
- [x] **T-050-67 — L0.4 w0-hooks.** `W:` `hooks/pre_gate.py`, tests · `blocked by:` none · `delivers:` §6 W0 · Δ −11/−412.
- [x] **T-050-68 — L0.5 w0-clitests.** `W:` tests · `blocked by:` none · `delivers:` §6 W0 · Δ 0/−506.
- [x] **T-050-69 — L0.6 w0-ctests.** `W:` tests · `blocked by:` none · `delivers:` §6 W0 · Δ 0/−560.
- [x] **T-050-70 — L1.1 core folds.** `W:` `core/`, `i/ledger_scripts.py`, `container.py`, tests · `blocked by:` T-050-65 · `delivers:` `sa-ledger-script-paths-in-two-tables`, `sa-session-liveness-has-two-rules` · Δ −93/−141.
- [x] **T-050-71 — L1.3 infra items (§4a 1–11).** `W:` `i/`, tests · `blocked by:` T-050-64 · `delivers:` `sa-privacy-match-has-two-matchers`, `sa-denylist-file-has-three-shapes` · Δ −343/−100.
- [x] **T-050-72 — L1.4 specs items (§4a 14–17).** `W:` `f/specs/`, tests · `blocked by:` T-050-66 · `delivers:` SPEC-DOC-046/028/037/007 gone · Δ −141/−135.
- [x] **T-050-73 — L1.5 cli/core items (§4a 12, 13, 18–20).** `W:` `cli/commands/migrate.py`, `f/{migrate,chokepoints,reconcile}/`, `core/session_store.py`, tests · `blocked by:` T-050-70 · `delivers:` `sa-path-segment-judged-by-two-matchers` · Δ −351/−238.
- [x] **T-050-74 — L1.6 test-only items (§4a 21–29; `TestAutopilot` kept).** `W:` tests · `blocked by:` T-050-69 · `delivers:` §6 W1 · Δ 0/−540.
- [ ] **T-050-75 — L2.9 hook dialects, one verifier.** `W:` `i/` · `blocked by:` T-050-41, -44, -52 · `delivers:` `sa-hook-files-written-by-table-and-by-hand`, `sa-projected-file-judged-by-four-verifiers` · Δ −360.
- [ ] **T-050-76 — L2.10 codex fold.** `W:` `i/`, `f/public/` · `blocked by:` T-050-41, -44, -52 · `delivers:` `sa-codex-effort-set-by-policy-and-by-tier`, `sa-frontmatter-split-five-ways` · Δ −160.
- [ ] **T-050-77 — L2.11 infra small.** `W:` `i/` · `blocked by:` T-050-41, -44, -52 · `delivers:` §6 W2c · Δ −235.
- [ ] **T-050-78 — L2.12 core.** `W:` `core/` · `blocked by:` T-050-41, -44, -52 · `delivers:` `sa-json-schema-validated-by-two-engines`, `sa-agent-model-resolved-by-two-modules` · Δ −620.
- [ ] **T-050-79 — L2.13 cli-features.** `W:` `f/{spec_context,chokepoints,ci_preflight}/`, `cli/commands/context.py` · `blocked by:` T-050-41, -44, -52 · `delivers:` §6 W2c · Δ −420.
- [ ] **T-050-80 — L2.14 hooks.** `W:` `hooks/ctx_inject.py` · `blocked by:` T-050-41, -44, -52 · `delivers:` §6 W2c · Δ −50.
- [ ] **T-050-81 — L3.1 table merges.** `W:` `tests/*/infrastructure/**`, git trio · `blocked by:` T-050-75..80 · `delivers:` §6 W3 · Δ 0/−2301.
- [ ] **T-050-82 — L3.2 table merges.** `W:` `tests/unit/core/**`, `tests/unit/test_*.py` · `blocked by:` T-050-75..80 · `delivers:` §6 W3 · Δ 0/−1798.
- [ ] **T-050-83 — L3.3 table merges.** `W:` `tests/unit/features/{specs,backlog}/**` · `blocked by:` T-050-75..80 · `delivers:` §6 W3 · Δ 0/−1097.
- [ ] **T-050-84 — L3.4 table merges.** `W:` `tests/unit/{hooks,skills,public}/**` · `blocked by:` T-050-75..80 · `delivers:` §6 W3 · Δ 0/−1086.
- [ ] **T-050-85 — L3.5 table merges.** `W:` other `tests/unit/**` · `blocked by:` T-050-75..80 · `delivers:` §6 W3 · Δ 0/−3325.
- [ ] **T-050-86 — L3.6 table merges.** `W:` `tests/contract/**` · `blocked by:` T-050-75..80 · `delivers:` §6 W3 · Δ 0/−4190.
- [ ] **T-050-87 — L3.7 table merges.** `W:` `tests/{integration,e2e}/**` · `blocked by:` T-050-75..80 · `delivers:` §6 W3 · Δ 0/−3940.
- [ ] **T-050-88 — L4.1 trim.** `W:` `i/` · `blocked by:` T-050-81..87 · `delivers:` §6 W4 · Δ −1697/0.
- [ ] **T-050-89 — L4.2 trim.** `W:` `core/`, top-level modules · `blocked by:` T-050-81..87 · `delivers:` §6 W4 · Δ −1070/0.
- [ ] **T-050-90 — L4.3 trim.** `W:` `f/{specs,backlog}/` · `blocked by:` T-050-81..87 · `delivers:` §6 W4 · Δ −1011/0.
- [ ] **T-050-91 — L4.4 trim.** `W:` `pub/**/*.py`, `hooks/` · `blocked by:` T-050-81..87 · `delivers:` §6 W4 · Δ −511/0.
- [ ] **T-050-92 — L4.5 trim.** `W:` `cli/`, other `f/` · `blocked by:` T-050-81..87 · `delivers:` §6 W4 · Δ −1256/0.
- [ ] **T-050-93 — L4.6–L4.12 test narration.** `W:` tests, one commit per W3 lane · `blocked by:` T-050-88..92 · `delivers:` §6 W4 · Δ 0/−2527.

### C — closure evidence (FR7, FR8, FR9)

- [ ] **T-050-62 — Prune and measure.** Execute the QA-lens pruning verdict (≥ 522 test lines, AC9.9); AC8.1 deltas, allowance subset, mutmut, AC9.11 counts, fenced rubric.
  `W:` tests, handoff · `blocked by:` T-050-23..93 · `delivers:` AC7.1–7.3, AC8.1, AC9.9–9.11 · `RED:` n/a.
