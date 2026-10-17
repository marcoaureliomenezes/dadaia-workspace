# Job 2 — Foundation: delete the `plain` tree type, add the `DADAIA_WT` marker (FR2)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- The plain type is deleted (operator 'Apagar o tipo plain'); the `[protected]` glob miss `protected-globs-miss-a-plain-tree-path` is a hotfix outside the rc and outside this job (`specs/bugs/AGENTS.md` §2), so this job carries no `block:` line and has no merge-first rule. Job 4 depends on that hotfix, not on this job's deletion, for protection at every depth.
- Built in the OLD layout. DELETE: `plain()`, the `plain` alternative of `NAME_RE`, `record_base`, the plain half of `recorded_base`, `_plain_base`, the plain row of `_kind_checks`, the `branch.<b>.dadaia-base` git config (ASIS §1.1 'base'). Defect C's third answer (`_plain_base`) goes with it.
- **Operator ruling 'Converter em teste de recusa'.** No test is deleted. Each plain-only test becomes a refusal test: a plain name (`new r maintenance`, `merge`/`preflight` of a one-segment tree) is refused as 'not a worktree name' with the `worktree list` fix line. Plain-only tests: `test__worktree_new.py:135,176,249`; `test__worktree_end.py:612,631` plus the `dadaia-base` assert at `:640`; `test__worktree_end__preflight.py:134`; `test__worktree_end__verdict_binding.py:170`. Tests that only use plain as an example tree are ported to a job tree, every assert intact (`assert` count per file unchanged; the reviewer diff-checks): `test__worktree_end__removal.py:77-91`, `test__worktree_end__preflight.py:186-220`, `test__worktree_end__scaffold.py:120`.
- `DADAIA_WT=1` joins the scrubbed env of every skill-script git child (`_git.scrubbed_env`, the one builder) and of `infrastructure/git_subprocess._run`, which already builds its env from it; the Job 4 hook honours the marker. Doctor's SKILL-MD-LENGTH fix stops opening a plain tree (`doctor.py:164-176`).
- Commit bodies: Phase 0 block `caused_by: none`, `prior diffs read: …`, `rebuild: none` (DELETE of a type).

Tasks: 8 (4 jr, 4 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: Three independent chains start together: {T1→T2}, {T3,T4,T5→T6}, {T7→T8}.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J2.T1 | sr | AC2.1 | `tests/public/skills/dd_bug_resolution/scripts/test__git.py` | RED: `scrubbed_env()` and the env `git_subprocess._run` builds carry the literal `{"DADAIA_WT": "1"}` and still drop repo-selecting `GIT_*` |
| J2.T2 | jr | AC2.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_git.py` | `scrubbed_env` gains one key (≈ +2 lines); owner T1. After T1 |
| J2.T3 | sr | AC2.2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` | RED: the five plain-only tests of these two files become refusal tests (`new r maintenance` exits 1 with `not a worktree name` and the list fix; `merge`/`preflight` of a plain name refuse likewise; the `dadaia-base` assert becomes 'no base is recorded in git config'); the commit body names the ruling |
| J2.T4 | sr | AC2.2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__preflight.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__verdict_binding.py` | RED: `:134` and `:170` become refusal tests; the preflight kind params at `:186-220` run on a job tree with identical asserts. Parallel with T3 (disjoint `W:`) |
| J2.T5 | jr | AC2.2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__removal.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__scaffold.py` | strength-preserving port of the example-only tests to a job tree; `assert` count per file unchanged. Parallel with T3, T4 |
| J2.T6 | jr | AC2.2 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_names.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` | DELETE per the intro (≈ −45 lines); owners T3, T4, T5. After T3, T4, T5. |
| J2.T7 | sr | AC2.3 | `tests/cli/commands/test_doctor__workspace_fix_lines_clear_their_finding.py` | RED: the SKILL-MD-LENGTH fix is the literal `Agent action: add the split of <skill>/SKILL.md to a task of the open rc, then run public install` and still clears its finding. Parallel with T1, T3 |
| J2.T8 | jr | AC2.3 | `dadaia_workspace/features/spec_context/doctor.py` | `_split_skill_fix` (≈ −3 lines); owner T7. After T7 |
