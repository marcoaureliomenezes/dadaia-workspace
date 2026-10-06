# TASKS — 0.5.0 rc-9, Reconciliation

**Status:** Approved — operator ruling 2026-10-05 (AskUserQuestion): "Aprovo (Recommended)", on 700217aa3 (recorded in baf8fe6aa).

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

## Stage JR.S1 — RED (none: AC6.1–AC6.4 have no test)

- Contract: no acceptance test exists for AC6.1–AC6.4 (ledger, ADR and memory only); no task rows.

## Stage JR.S2 — (AC6.1–AC6.3)

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only); envelope `specs/memory/**`, `specs/memory/product/catalog.json`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/releases/0.5.0/_RELEASE.json`, `specs/ADRs/decisions.jsonl`; ACs AC6.1–AC6.3
- ACs served: AC6.1–AC6.3.
- Envelope: `specs/memory/**`, `specs/memory/product/catalog.json`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/releases/0.5.0/_RELEASE.json`, `specs/ADRs/decisions.jsonl`.
- Exit tests: `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S2.T1 | AC6.1 | `specs/memory/**`, its derived docs and `catalog.json`, in one merge (AC1.5) |  |
| JR.S2.T2 | AC6.1 (F131) | `specs/audits/20260930-structural-convergence/FINDINGS.jsonl` |  |
| JR.S2.T3 | AC6.2 | `specs/releases/0.5.0/_RELEASE.json` (`log`) |  |
| JR.S2.T4 | AC6.3 | `specs/ADRs/decisions.jsonl` (`measured_by` repairs; acceptance is the operator's) |  |

## Stage JR.S3 — bug law per ADR 0206 (corrective)

- Contract: the bugs, releases and worktree laws, the bug skills, RC-FLOW, CONTEXT.md and the memory state ADR 0206's law (no rc closes with an open bug; the bug batch; the next rc's `## Bug window review` judges the fixes), replacing 0201/0204's next-Job-1 clauses; the canon stamp re-recorded.
- ACs served: ADR 0206.
- Envelope: `specs/ADRs/decisions.jsonl`, `public/scaffold/bugs/AGENTS.md`, `specs/bugs/AGENTS.md`, `public/scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md`, `bugres/SKILL.md`, `relimpl/RC-FLOW.md`, `public/skills/dd-release-definition/SKILL.md`, `public/data/worktrees-AGENTS.md`, `CONTEXT.md`, `specs/memory/**`, `docs/*.md`, `core/specs_version.py`, `public/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py`.
- Exit tests: `tests/unit/core/test_specs_version.py`, `tests/unit/features/specs/test_tree5_shipped_history.py`, `tests/contract/test_docs_derived_from_memory.py`, `tests/contract/test_law_states_what_the_code_does.py`, `tests/contract/test_behavior_map.py`, `tests/integration/test_doctor_fix_lines_clear_their_finding.py`; `bugs.py check`, `release.py check`, `dadaia doctor` clean.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S3.T1 | ADR 0206 | `specs/ADRs/decisions.jsonl`, `public/scaffold/bugs/AGENTS.md`, `specs/bugs/AGENTS.md`, `public/scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md`, `bugres/SKILL.md`, `relimpl/RC-FLOW.md`, `public/skills/dd-release-definition/SKILL.md`, `public/data/worktrees-AGENTS.md`, `CONTEXT.md`, `specs/memory/**`, `docs/*.md`, `core/specs_version.py`, `public/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py` | the stage's exit tests |

## Stage JR.S4 — (AC6.4)

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only); envelope `specs/releases/0.5.0/_RELEASE.json`, `specs/releases/0.5.0/rc-10/SPEC.md`; ACs AC6.4
- ACs served: AC6.4.
- Envelope: `specs/releases/0.5.0/_RELEASE.json`, `specs/releases/0.5.0/rc-10/SPEC.md`.
- Exit tests: `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S4.T1 | AC6.4 | `specs/releases/0.5.0/_RELEASE.json` (phase), `specs/releases/0.5.0/rc-10/SPEC.md` (Draft, in the `0.5.0-rc10/define` tree) |  |
| JR.S4.T2 | — | generated only: the behavior-map hashes and derived docs | close task: test-audit + mutation-diff over the job diff (Q23), regenerate the behavior map and derived docs (R6), write `done` (Q9) |
- The close task runs last, after every other task of its stage has fast-forwarded onto the job branch; its mutation-diff and test-audit run even in a stage whose gate is validators only (Q23).

- Done: the Reconciliation job closed by JR.S4.T2 (2026-10-05); behavior map and derived docs current (owner tests green, nothing regenerated).

## Stage JR.S5 — bug batch inside Reconciliation (ADR 0206)

- Contract: the two LOW bugs registered at 20e5d74d2 resolved, each by one shape-3 commit with its RED case; `bugs.py status` shows no rc-9 bug open; `ci.py job`'s doctor no longer warns TREE-5/MEM-DRIFT-2 about `specs/AGENTS.md`.
- ACs served: ADR 0206.
- Envelope (`specs/bugs/BUGS.jsonl` lines ride each fix commit, outside both write sets): `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`, `dadaia_workspace/public/entities/behavior-map.json` (regenerated hashes), `.gitignore`, `specs/AGENTS.md`, `tests/contract/test_copy_drift_scoped_law.py`, `scripts/guards/repo.py`, `specs/bugs/BUGS.jsonl`.
- Exit tests: `tests/unit/skills/test_bug_resolution_bugs_script.py`, `tests/contract/test_copy_drift_scoped_law.py`, `tests/contract/test_behavior_map.py`; `bugs.py check`, `ci.py job` green.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S5.T1 | bugs-fix-lists-one-commit-twice | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`, `dadaia_workspace/public/entities/behavior-map.json` (the regenerated scripts hash) | `tests/unit/skills/test_bug_resolution_bugs_script.py` (new case) |
| JR.S5.T2 | specs-law-file-untracked-by-gitignore — reverted at fbb40069a (guard `specs-canon-tracked` required the law ignored); redone by JR.S5.T3 | — | — |
| JR.S5.T3 | specs-law-file-untracked-by-gitignore (operator ruling 2026-10-06, verbatim: "Corrige assim na rc-9 (Recommended)" — handoff `.dadaia/handoff/dadaia-workspace/2026-10-06T044417Z-main-thread-rc9-bug-rulings.handoff.json`; the design wording is the agent's, not ruled: `specs-canon-tracked` expects every canon row tracked, drift is TREE-5's in CI's doctor) | `.gitignore`, `specs/AGENTS.md`, `scripts/guards/repo.py`, `tests/contract/test_copy_drift_scoped_law.py` | `tests/contract/test_copy_drift_scoped_law.py` (new case) |

## Stage JR.S6 — bug batch inside Reconciliation, second pass (ADR 0206)

- Contract: the two bugs registered by `chore(bugs): report memory-window-bound-unreachable-from-head, bugs-fix-counts-a-reverted-fix` resolved, each by one shape-3 commit with its RED case: a window bound HEAD cannot reach is refused locally as a clean clone refuses it, with a `fix:` line; a fix commit a later `Revert "…"` undid drops out of `bugs.py fix`; review LOW-3: the checked-out-tree case writes no object and takes no index lock; `bugs.py status` shows no rc-9 bug open. A stage of its own: its `W:` sets meet JR.S5's (`bugs.py`, the behavior map, `test_copy_drift_scoped_law.py`).
- ACs served: ADR 0206.
- Envelope (`specs/bugs/BUGS.jsonl` lines ride each fix commit, outside every write set): `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_drift.py`, `tests/unit/skills/test_memory_drift.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`, `tests/contract/test_copy_drift_scoped_law.py`, `dadaia_workspace/public/entities/behavior-map.json` (regenerated hashes), `specs/bugs/BUGS.jsonl`.
- Exit tests: `tests/unit/skills/test_memory_drift.py`, `tests/integration/test_shallow_history_fix_line_clears.py`, `tests/unit/features/specs/test_release_tree.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`, `tests/contract/test_copy_drift_scoped_law.py`, `tests/contract/test_behavior_map.py`; `bugs.py check`, `ci.py job` green.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S6.T1 | memory-window-bound-unreachable-from-head | `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_drift.py`, `tests/unit/skills/test_memory_drift.py` | `tests/unit/skills/test_memory_drift.py` (new case: a bound HEAD does not reach refuses with a `fix:` line); RED before the fix |
| JR.S6.T2 | bugs-fix-counts-a-reverted-fix | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py` | `tests/unit/skills/test_bug_resolution_bugs_script.py` (new case: a fix commit a later `Revert "…"` undid is not listed); RED before the fix |
| JR.S6.T3 | review LOW-3 | `tests/contract/test_copy_drift_scoped_law.py` | the same file: the checked-out-tree case reads the tracked tree with no index lock and no object write; every assert line byte-identical |
| JR.S6.T4 | — | generated only: `dadaia_workspace/public/entities/behavior-map.json` | close task, last: regenerate the behavior map, test-audit + mutation-diff over the stage diff (Q23) |
