# TASKS — 0.5.0 rc-10, Job 1 — the fix reader and the window's instruments

**Status:** Approved — by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Every stage before Job 6 merges runs under today's law (SPEC.md Job 6): stage 1 RED as strict xfail.

- Precondition: the main thread's `docs(adr): accept 0208–0210` commit, written at the rebase.

## Stage J1.S1 — RED

- Contract: exit tests every AC1.1/AC1.2 unit row RED as strict xfail; envelope `tests/unit/skills/test_bug_resolution_bugs_script.py`; ACs AC1.1, AC1.2

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J1.S1.T1 | AC1.1, AC1.2 | `tests/unit/skills/test_bug_resolution_bugs_script.py` | RED: shape-4 resolve over two task commits → summed numstat, literal direction; class commit links its body ids; later overlapping `fix(bugs)` → 1 overfitting, a REBUILD → 1 planned; two rcs untouched → settled; seam present / untracked / absent node / parametrized node / `TestX::test_y` / non-test tracked file / window row with a deleted seam. c9faccfdc's and JR.S6.T2's rows stay byte-identical |
- Rows the window gains at the rebase (PLAN): a REBUILD row needing a new RED case adds its case to J1.S1.T1's rows (the rows are known before the job opens); a KEEP row needs none.

## Stage J1.S2 — REBUILD the reader; law text

- Contract: exit tests J1.S1's AC1.1 rows green, unit + integration green; envelope `bugres/scripts/bugs.py`, `bugres/scripts/_bugs_fix.py`, `S/dd-audit-project/PILLAR-BUGS.md`, `S/dd-release-definition/SKILL.md`, `bugres/LINEAGE.md`, `pub/scaffold/bugs/AGENTS.md`, `specs/bugs/AGENTS.md`, `S/dd-code-review/SKILL.md`, the canon pin; ACs AC1.1, AC1.3–AC1.5

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J1.S2.T1 | AC1.1 | `bugres/scripts/_bugs_fix.py` (new: link, diff, fix surface, rework, settled), `bugres/scripts/bugs.py` (`_fixes`, `_direction` and the `None` arm leave; `fix`, `stats`, `window`, `_candidates` call the one reader) | `test_bug_resolution_bugs_script.py`; commit `refactor(J1.S2.T1): REBUILD the fix reader — …` |
| J1.S2.T2 | AC1.1, AC1.4 | `S/dd-audit-project/PILLAR-BUGS.md` (:8 rewritten; ninth metric, target 100 %) | no test; check: `grep -c 'rebuild: none — <reason>'` ≥ 1 |
| J1.S2.T3 | AC1.3 | `S/dd-release-definition/SKILL.md` (§1: the overfitting patterns, KEEP or REBUILD) | no test |
| J1.S2.T4 | AC1.4 | `bugres/LINEAGE.md` (step 7: one producer of the `rebuild:` line) | no test; same grep check |
| J1.S2.T5 | AC1.5 | `pub/scaffold/bugs/AGENTS.md`, `specs/bugs/AGENTS.md` (by `specs upgrade`), `S/dd-code-review/SKILL.md`, `core/specs_version.py`, `pub/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py` (the pin re-record) | `test_specs_version.py`, `test_tree5_shipped_history.py` |

## Stage J1.S3 — evidence_seam; absorbed window rows; close

- Contract: exit tests J1.S1's AC1.2 rows green, no xfail left for AC1.1/AC1.2, unit + integration green; envelope `bugres/scripts/_bugs_transition.py`, `bugres/scripts/bugs.py`, the born rows' `W:`, this file; ACs AC1.2, the added window rows

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J1.S3.T1 | AC1.2 | `bugres/scripts/_bugs_transition.py` (`evidence_seam` required; textual check of path and `::` segments, brackets stripped), `bugres/scripts/bugs.py` (resolve passes the tracked-file read; `window` marks a gone seam file) | `test_bug_resolution_bugs_script.py` |
| J1.S3.T2+ | the window rows added at the rebase | per row, disjoint from T1 and from each other; a row meeting another's `W:` moves to a Stage J1.S4, and the close task with it | born at the rebase: one REBUILD per row, keeping the fix's tests; `bugs-fix-counts-a-reverted-fix` is AC1.1's unit and needs no row |
| J1.S3.T9 | — | this file | close task, last: behavior map regenerated; `test-audit:` and `mutation:` lines in its body (Q23); `done` |
