# Job 5 — the one-owner residue: one scrubbed git call, one refusal template (FR4)

**Status:** Draft

Wave 2. Two real duplicates remain of rc-14's G1 grep (AS-IS read each hit): `bugs.py` runs an unscrubbed `git ls-files` beside `_git.git`, and the refusal "the resulting … would not pass check — nothing was written" is assembled three times (`_commit.py`, `_backlog_store.py`, `_release_store.py`). Everything else the entry listed stays, with its reason, in PLAN §1.3. No comment is added at the KEEP sites.

- **Seams closed.**
  - `bugs.py` calls `_git.git(specs, "ls-files", "--full-name", ":/")` and maps `RuntimeError` to the same `Refusal` it raises today.
  - `_commit.validated` is the only place the sentence is built; its signature is the implementer's choice inside these limits: `git grep -n 'would not pass check' -- dadaia_workspace/public/skills` returns one line, the backlog and release stores call it, `_bugs_store.py` follows any signature change, and every existing store test stays green unedited. A second wrapper around it is a layer; stop and return the seam instead.
  - `_release_store.validated` may stay as a thin caller (`_release_new.py` uses it).
- Test-side first: T1. Then T2, T3 (disjoint `W:`).
- Commit bodies carry `git grep -n '_commit\.commit(' -- dadaia_workspace/public/skills` (3 before and after) and the `would not pass check` count (3 before, 1 after).
- Pre-review checklist: one scrub, one template; no cross-component import; sweep lines; net lines about −17 (est.).

Tasks: 3 (0 jr, 3 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J5.T1 | sr | AC4.1 | `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py` | RED, unit: with `GIT_DIR` and `GIT_WORK_TREE` on another repo, `bugs.py append` judges `--surface` against its own repo's tracked directories (a directory tracked only in the other repo is refused). Owner this file |
| J5.T2 | sr | AC4.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py` | the git call goes through `_git.git`. Fix commit of the unscrubbed-call residue of `skill-git-runners-read-the-callers-git-env`; Phase 0 block `prior diffs read: 9c5911a51`. Owner T1. After T1 |
| J5.T3 | sr | AC4.2 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_commit.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_store.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_store.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_store.py` | REBUILD: the two inline copies call `_commit.validated`. Owners: the existing store suites, unedited |
