# Job 1 — stats refuses a release state that breaks its schema (FR1, R1)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1, §1.1, §2.

- **Shape (T4).** `_stats.table` runs `release.py check --specs <specs>` through `_script` with `ok=(0, 1)` before any parse and raises its Refusal from check's first `error` line and its one `fix:` line, as `_worktree_end._refuse_red` relays a red script (the kernel's `_refusal` helpers). The refusal check prints for each finding is the message; stats adds none. Then the state is read once with `json.loads`, which a passed check makes total: `_window` takes no guard, and the `fix = act(...)`/`parse_object` lines and their imports go. A version with no release folder never reaches the parse (`n/a`, exit 0).
- **Shape (T5, seam J1-a).** `_refuse_unready` runs the instance's `release.py check --specs <wt-rc tree>/specs` and relays its refusal; the `parse_object`/`Unreadable` block goes, `phase` is read from the checked document, the wrong-phase refusal text is unchanged. The rc tree is where the branch is checked out; if a case shows the tree can be absent while its branch exists, T5 returns the gap to the main thread before editing.
- **Probe (B9).** `release.py check` on a non-UTF-8 `_RELEASE.json` prints a `LEDGER-RELEASE-SCHEMA error` finding with one `fix:` line and no traceback (probed 2026-10-19 on a scratch copy); no check change is needed, and T1 covers the case.
- **Cost.** Stats gains one `release.py check` run: 0.1 s on this tree (as-is review, measured 2026-10-19).

**Gate law.** `verify:` is `python scripts/ci.py job` (lint, typecheck, guards, unit-fast, doctor; `scripts/ci.py:88`), no change. Definition of done: that run, the touched test directories (`tests/public/skills/dd_handoff_emitter`, `tests/public/skills/dd_gitflow_default`), the own-diff self-check over `git diff <base>...HEAD` (no removed `assert` outside T2's named moves, no new skip), and the sweep greps. No preflight, no full CI line.

**Sweep greps.** `git grep -nE "parse_object|read_text\(path" -- dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py` prints nothing; `git grep -n "Unreadable" -- dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py` prints nothing; `git grep -nE "_RELEASE|STATE" -- dadaia_workspace/public/skills/*/scripts/*.py` hits are listed in the T5 commit body, each judged reader or writer.

Tasks: 6 (1 jr, 5 sr). Order: T1, T2 and T3 start together (T1, T2 share a file: T1 first); T4 after T1 and T2; T5 after T3; T6 any time.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J1.T1 | sr | AC1.1 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | RED, unit, `test(stats-crashes-on-a-release-state-that-breaks-its-schema): ...`: `verdict.py stats 0.5.0-rc18 --specs <tree>` on a state with (a) a log entry without `ts`, (b) a `candidate` of `foo`, (c) a non-object log entry exits 1, no traceback, one `[error]` and one `fix:` line equal to `release.py check`'s for that finding (literals); a milestone without `sha` still prints `n/a`; a non-UTF-8 state gives check's UTF-8 finding |
| J1.T2 | sr | AC1.3 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | `test(...)` naming the stats-reader ruling ("Run release.py check first"): the expected message and fix line of `test_stats_of_an_unreadable_release_state_is_refused_with_one_fix_line` become check's for `{bad`, `[]` and non-UTF-8, cases and exit code kept; the no-release-folder `n/a` cases stay unchanged |
| J1.T3 | sr | AC1.4 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py` | RED, unit: `new` of a job on a `wt-rc` whose `_RELEASE.json` breaks the schema refuses with check's finding and fix line; IMPLEMENTATION opens; the wrong-phase refusal text is unchanged |
| J1.T4 | sr | AC1.1, AC1.2, AC1.3 | `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py` | REBUILD (R1): the shape above; owner `test_verdict.py`; the five prior stats fixes' contract tests stay green; net lines at most 0 |
| J1.T5 | sr | AC1.4 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py` | REBUILD of `_refuse_unready` (seam J1-a); owner `test__worktree_new.py`; net lines at most 0 |
| J1.T6 | jr | AC1.4, AC1.5 | `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md` | line 55 states that stats refuses a release state `release.py check` refuses and that the closure readout runs after the memory pass (check refuses CLOSURE until it is recorded); no test |
