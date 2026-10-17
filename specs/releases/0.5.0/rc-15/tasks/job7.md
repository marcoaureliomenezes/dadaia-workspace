# Job 7 — the backlog exit reads the `--release` SPEC only (FR6)

**Status:** Draft

Wave 3. Bug `backlog-exit-refuses-on-an-unrelated-spec-origin`, REBUILD of `_picks`/`_release` in `_backlog_exit.py` (4 ledger bugs on the unit; the strict global scan came with `e3e5b747d`, whose body states the open bug's behaviour). One scan answered two questions (does the `--release` SPEC name the slug; which release picked it, for the fix line). The law asks the first only.

- **Seams closed.**
  - `_release` reads `releases/<--release>/rc-*/SPEC.md` through `release.py origin`, per SPEC; an unreadable Origin in that release still refuses (it is the law's question). `_picks` and the latest-picking-release suggestion are deleted, not made tolerant.
  - A missing `--release` refuses with `Operator action:` naming the flag, no placeholder.
  - The refusal's one `fix:` line is `Operator action: name <slug> in the backlog: clause of the first **Origin:** line of a SPEC under <specs>/releases/<--release>, then rerun this exit.` with the real values.
  - **Ordered change (AC6.2).** `test_the_refusal_fix_names_the_latest_picking_release_by_version` (`test_backlog.py:284-298`) asserts the fix ends in `--release 0.10.0`. Its assert changes to the line above for `--release 9.9.9`, naming neither 0.9.0 nor 0.10.0, in a `test(J7.T2)` commit that names the operator's order of 2026-10-13: "Só a --release (Recommended)". The test is renamed to its new contract in the same commit. `test_delivered_outside_the_release_origin_is_refused` (no `<`, no `rejected`) stays unedited.
- Test-side first: T1, T2 (same file, in order). Then T3.
- Commit bodies carry `git grep -n '_picks\|latest' -- dadaia_workspace/public/skills/dd-backlog-definition` (before, 0 after) and the Phase 0 block `caused_by: J11.T2`, `prior diffs read: e3e5b747d`, `rebuild: _picks, _release`.
- Pre-review checklist: one reader decides; no cross-component import (the Origin read still runs `release.py`); sweep line; net lines about −8.

Tasks: 3 (0 jr, 3 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J7.T1 | sr | AC6.1 | `tests/public/skills/dd_backlog_definition/scripts/test_backlog.py` | RED, integration: another candidate holds an Origin-less draft SPEC; `exit <slug> --disposition delivered --release <id>` exits 0 when `<id>`'s SPEC names the slug. Owner this file |
| J7.T2 | sr | AC6.2 | `tests/public/skills/dd_backlog_definition/scripts/test_backlog.py` | the ordered assert change of the intro, quoting the order. After T1 |
| J7.T3 | sr | AC6.1, AC6.3 | `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_exit.py` | REBUILD as the intro says. Owners T1, T2. After T2. Fix commit of the bug |
