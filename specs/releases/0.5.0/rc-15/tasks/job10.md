# Job 10 — the DEFINITION done-marker check leaves (FR11)

**Status:** Draft

Wave 3, after Job 6 (both edit `_release_tree.py` and the thin-wrapper test) and after the hotfix `release-check-memory-task-check-reads-retired-tasks-md` merges (outside the DAG; unmerged at define time, feature tip `a06df6284`). Job files carry no `[x]`/`[-]` markers, so the check reads markers only from the retired `TASKS.md` and never fires on a current candidate. Operator order, 2026-10-13: "Apagar check e testes (Recommended)".

- **Seams closed.**
  - The main thread names the hotfix's merged sha in the dispatch brief; T2 deletes the tests that hotfix added for the `TASKS.md` read alone, found with `git show <sha> -- tests`. If the hotfix is not merged, or `_memory_tasks` still exists, T3 stops.
  - The `test_release.py:324` assert is `MARK_RE.finditer("-\n\n- [ ]**T-1**") == […]`: it judges the regex and nothing else, so it is covered by the order ("MARK_RE/MARKS and tests that exist only for the deleted check", main thread 2026-10-13). The rest of `test_writes_reads_rc6_t_050_117_to_its_ten_paths` (the `writes` asserts) stays. The `_OWNERS` entry of `_release_schema.py` in the thin-wrapper test loses the names `MARK_RE` and `MARKS` in the same commit. If the dispatch brief does not repeat that ruling, T2 stops there.
  - `MARK_RE` and `MARKS` leave `_release_schema.py` only if `git grep -nE 'MARK_RE|MARKS\b'` finds no reader once T2 and the `_release_tree.py` edit are in (today `MARKS` has none).
  - **Setup move (AC11.2), main-thread ruling named in `test(J10.T1)`.** `test_a_definition_finding_stamps_the_commit_that_touched_the_trio` keeps its assert; its trigger changes from the default ticked task to a closure entry logged after the birth note (the `("x", "dispositions")` log of the neighbouring rows). The closure-entry rows of `test_check_judges_a_definition_release` stay unedited.
- Test-side first: T1, then T2 (same file, in order). Then T3.
- Commit bodies carry `git grep -n 'TASKS.md' -- dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` (hits before, 0 after) and the `MARK_RE|MARKS` grep.
- Pre-review checklist: one reader of release state; sweep lines; net lines about −15.

Tasks: 3 (1 jr, 2 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J10.T1 | sr | AC11.2 | `tests/public/skills/dd_release_implementation/scripts/test_release.py` | the setup move of the intro, naming the main-thread ruling; the assert is untouched and the test stays green |
| J10.T2 | sr | AC11.1, AC11.3 | `tests/public/skills/dd_release_implementation/scripts/test_release.py`, `tests/infrastructure/test_public_assets__public_scripts_thin_wrapper.py` | the deletions of the intro (the two marker rows, the `:324` assert, the hotfix's marker-only tests, the two `_OWNERS` names) in one `test(J10.T2)` commit quoting "Apagar check e testes (Recommended)". After T1 |
| J10.T3 | jr | AC11.1, AC11.3 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py` | the marker half of `_definition_findings`, its `marks` parameter, the `TASKS.md` read and the `MARK_RE` import leave; `MARK_RE`/`MARKS` leave `_release_schema.py` under the grep condition; the docstring states the closure-entry contract only. Owner: the existing release suites. After T2 |
