# Job 3 — bytecode-off has one env owner (FR2)

**Status:** Draft

Wave 1. `scrubbed_env()` of the kernel's `_git.py` already builds the child env of every skill-script spawn, so it carries the variable; five env sites that build a child env by hand drop their own literal (Q2 option B, agent default). The class has 8+ ledger bugs (`hook-runtimes-create-repo-bytecode`, `skill-owner-tests-write-bytecode-into-the-source-tree`, `job-gate-red-on-untracked-bytecode`, `test-suite-writes-outside-tmp`, …): the cause is that each new spawner must remember. An owner function does not stop a forgetful spawner; the repo-tree write tripwire of `tests/conftest.py` is the class's one catch and stays unedited (AC2.4). The sites that stay, with reasons, are PLAN §1.2.

- **Seams closed.**
  - The owner API is `scrubbed_env(parent: Mapping[str, str] | None = None)`: `parent` defaults to `os.environ`. A site whose base is a caller-supplied mapping (`suite_env`'s `parent`, `fenced_env`'s result) passes it; the key is set to `1` unconditionally, so a `0` in the parent does not survive.
  - `GIT_*` repo selectors leaving those five child envs is accepted: it is the kernel's rule for every spawn.
  - `scripts/ci.py` and `scripts/mutate.py` reach the owner as the guards do (`sys.path` gets the checkout, then `dadaia_workspace.core.skill_owner.load_owner("dd-bug-resolution", "_git")`); the loader and the owner are stdlib only, and the package `__init__` files are empty.
  - `suite_env`'s existing literal-expected test (`tests/fixtures/test_harness_env.py`, `unset` removes the key) stays green unedited; if a site cannot move without editing an existing assert, stop and return the seam: AC2.2 then names fewer sites, with the reason in PLAN §1.2.
- **Consumers.** `git grep -n 'scrubbed_env' -- dadaia_workspace tests scripts` before and after; every caller of the default call is unchanged.
- Test-side first: T1, T3 (disjoint `W:`). Then T2, T4.
- Commit bodies carry `git grep -nE 'PYTHONDONTWRITEBYTECODE|dont_write_bytecode|-B\b' -- dadaia_workspace scripts tests` (the hit set shrinks by the five literals and nothing else).
- Pre-review checklist: one owner of a child env; no cross-component import beyond the loader; sweep line above; no platform fact; net lines about 0 (five literals out, one parameter in).

Tasks: 4 (0 jr, 4 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J3.T1 | sr | AC2.1 | `tests/public/skills/dd_bug_resolution/scripts/test__git.py` | RED, unit: `scrubbed_env()` carries `PYTHONDONTWRITEBYTECODE=1` (also when the parent says `0`), and a child Python started with it from a temporary package writes no `__pycache__`. Owner this file |
| J3.T2 | sr | AC2.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_git.py` | `scrubbed_env` takes the optional parent and sets the key; the docstring states the contract (a child env: repo selectors out, no bytecode). Owner T1. After T1 |
| J3.T3 | sr | AC2.2 | `tests/fixtures/harness_env.py`, `tests/public/skills/dd_bug_resolution/scripts/test__atomic.py` | `suite_env` and the `_child` helper (`:216`) build on the owner and drop their literal; the `-B` argv at `:202,218` stays (a clean env or `-I` hides the variable). A `test(J3.T3)` commit of support code, no assert touched; `test_harness_env.py` and the full `test__atomic.py` stay green unedited |
| J3.T4 | sr | AC2.2 | `scripts/ci.py`, `scripts/mutate.py`, `dadaia_workspace/features/certification/service.py` | the three env sites build on the owner and drop their literal. Owner T1, the existing `test_ci.py`, `test_mutate.py` and certification suites unedited. After T2 |
