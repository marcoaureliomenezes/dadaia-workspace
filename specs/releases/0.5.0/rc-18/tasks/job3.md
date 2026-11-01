# Job 3 — the readout: a missing candidate is n/a, the window runs between CLOSUREs, no cross-skill import (FR2, FR3, R2)

**Status:** Draft

Wave 2, waits on Job 2. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and §1.1.

- **R2 REBUILD of `_stats.py`.** Structural cause: the unit owns three facts that belong elsewhere, and each prior fix patched one symptom. The bug-ledger read reaches into `_bugs_store` (the arithmetic of metrics 1 and 9 is the ledger's); the repo identity is a fourth copy of the common-dir derivation (`stats-names-the-repo-by-its-checkout-folder`); the window is built from log timestamps with sentinel defaults (`'9'`, `''`), so a candidate the log never names gets invented values (`stats-invents-a-table-for-a-missing-candidate`). After the rebuild: `_window` returns `None` for a candidate with no log entry and `table` prints `n/a` for every metric; the window of metrics 1 and 9 runs from the previous candidate's CLOSURE stamp (empty for the first) to this one's; the closed counts come from `bugs.py stats --closed-after/--closed-until` run as a script; the repo comes from `_git.main_checkout`. Net lines of `_stats.py` shrink.
- **AC2.4 choices.** `_merge` uses `--first-parent` instead of `--ancestry-path`: the back-merge `f9fc04f21` (integration merged into the work branch) is on the ancestry path but never on integration's first-parent line, so metrics 4 and 6 stop counting it; the test builds that history. The birth default `''` is gone with the sentinel rewrite; the test pins the first candidate's empty lower bound. The two stray `# fmt: skip` on the tuple closings go.
- **Prior diffs to read first.** `f3a3788ca`, `461c42e22`, `3612bb589`, `15a79e2dd`, `b652b93f1`, `655fb36be`, `04d82da9d`. The contract tests those fixes hardened stay green and unloosened (AC2.7).
- **AC5.1 callers.** `verdict.py`'s `reports validate` call and `_stats._context` are two of the `run_cli` callers: T1 tests root found plus CLI missing for each.

**Gate law (rc-18).** The job's `verify:` is `python scripts/ci.py job` (median 1m52, measured in rc-17; no `verify:` change). An implementer's definition of done is that run, plus the touched test directories (`tests/public/skills/dd_handoff_emitter`, `tests/public/skills/dd_bug_resolution`), plus the own-diff self-check over `git diff <base>...HEAD`: no removed `assert` line and no newly skipped test unless this file names the order, and the sweep greps. No preflight, no full CI line; CI on push is the net. A RED task fails only on its new RED tests and says which. Every task reads `.dadaia/tmp/main-thread/20261018/rc18-common.md`.

**Sweep greps.** `grep -n '_bugs_store\|git-common-dir\|fmt: skip' dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py` prints nothing; `git diff <base>...HEAD --shortstat -- dadaia_workspace` shows deletions at least equal to insertions.

Tasks: 2 (0 jr, 2 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T2 after T1.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J3.T1 | sr | AC2.1, AC2.2, AC2.3, AC2.4, AC2.7, AC5.1 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | RED, unit, literals: `stats 0.5.0-rc99` prints `n/a` for every metric; a bug closed between two candidates counts in exactly one window; the first candidate's empty lower bound; a back-merge fixture proves `--first-parent`; the reader works with the bug skill's internals unimportable; root found plus CLI missing refuses with one fix line |
| J3.T2 | sr | AC2.1, AC2.2, AC2.3, AC2.4, AC2.7, AC5.1 | `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py`, `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/verdict.py` | REBUILD `_stats.py` as designed above (`refactor(J3.T2): REBUILD _stats — …`); `verdict.py` only if the missing-candidate refusal or the `OSError` fix line needs its entry; turns T1 green |
| J3.T3 | sr | AC5.6 | `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py` | RED (`cebaf982a`): `fix_files` runs a constant number of git spawns |
| J3.T4 | sr | AC5.6 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_git.py` | `4612f5159`, `034dc9ac7`: `fix_files` checks reachability with one `rev-list HEAD` and drops its copy of the sha guard; turns T3 green |
| J3.T5 | sr | AC2.1, AC2.4, AC5.6 | `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | job-3 review RED (`84d6915e8`): the closure merge pick, a malformed candidate name, one reachability read |
| J3.T6 | sr | AC2.1, AC2.4, AC5.6 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_check.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_git.py`, `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py`, `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/verdict.py`, `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py` (main-thread `W:` amendment: `test_bugs.py`) | `41f2f41f1`, `45be2a437`: metric 4 takes the first first-parent integration merge holding the closure sha; a malformed candidate reads n/a; one reachability set for `check` and `fix_files`; turns T5 green |

**Closure record (main thread, 2026-10-18).** 4 tasks landed beyond the PLAN, the rows after the planned ones, read from `git log wt/0.5.0/rc-18/wt-rc`.

- Ruled, sweep line 1: it reads "no `fmt: skip` on a bare tuple closing"; the 8 one-line `fmt: skip` in `_stats.py` are the file's idiom.
- Ruled, sweep line 2 (net ≤ 0): net +3 against wt-rc is accepted for the two-read merge pick and the shared `reached`.
- Ruled, tests: `test_bugs.py`'s trace pins now assert by outcome; one `rev-list` read replaces the per-sha `merge-base`.
- `W:` amendment (main thread): J3.T6 writes `test_bugs.py`.
