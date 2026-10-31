# Job 8 — four stale facts: the registry stamp, the ssh probe, the dist-writer list (bug batch B)

**Status:** Draft

Wave 2, waits on — (no shared path; it sits in wave 2 by the agent cap of four, PLAN DAG). Paths are repository-relative to `repos/dadaia-workspace/`; `P/` = `dadaia_workspace/`. Design and evidence: PLAN §1, §1.2. Each non-null `caused_by` makes the fix a REBUILD (`refactor(bugs): <ids> — REBUILD <unit>: …`, with the `caused_by:`/`evidence:`/`prior diffs read:`/`rebuild:` block).

- **Stamp (T1, T2).** `P/infrastructure/json_context_store.py:23` `SCHEMA_VERSION` is the one stamp. `P/features/migrate/state_v2.py:38` returns `schema_version_before="2"` for a registry already at 2 or above: it returns the stamp the registry holds. `P/cli/commands/migrate.py:3,72` says "schema v1 to v2": it names no number the store owns. `scripts/CONSUMER_VALIDATION_RECIPE.md:28` (F-17) expects "schema_version 2 after migrate": it expects 3, and `test_certify.py` pins that literal, so the next stamp bump fails loudly instead of rotting. One group commit names `migrate-reports-a-stamp-three-registry-as-stamp-two, consumer-recipe-expects-stamp-two`. Lineage: `J4.T10` and `T-050-63`.
- **Reachability probe (T3, T4).** `reachable` (`P/infrastructure/git_subprocess.py:92-100`) sets `GIT_SSH_COMMAND="ssh -o BatchMode=yes"` outright, overriding the user's environment and `core.sshCommand`. It composes: the user's command (the environment variable, else `core.sshCommand`, else `ssh`) plus `-o BatchMode=yes`. Lineage: `J6.T8`.
- **Dist writers (T5, T6).** `S/dd-cli-library/SKILL.md:28` lists what writes `repos/` and `.dadaia/dist/`. It names `worktree pause` and `worktree resume` beside `export` and `init --from` (`_worktree_pause.py:3`). Lineage: `J3.T7`. The skill is a library source; reproject after the merge (PLAN §2).
- **Lineage (main thread, in this job's `wt-main`).** Before each REBUILD task: `bugs.py update --set caused_by=<value> <id>` (PLAN §1.2); after it merges: `resolve --caused-by <value>`.
- **Contract tests that stay green, unloosened:** `tests/cli/commands/test_migrate.py` (the stamp the registry carries after migrate), `tests/cli/commands/test_certify.py` (the recipe's commands exist in the live tree), the reachability cases in `tests/infrastructure/test_git_subprocess*.py`.

**Gate law.** `verify:` is `python scripts/ci.py job`, no change. Definition of done: that run, `tests/cli/commands/test_migrate.py`, `tests/cli/commands/test_certify.py`, `tests/infrastructure`, `tests/public/skills/dd_cli_library`, `tests/features/migrate`, the own-diff self-check, the sweep greps.

**Sweep greps.** `git grep -nE 'schema_version_before="2"|v1 to v2' -- dadaia_workspace` prints nothing; `git grep -n "BatchMode" -- dadaia_workspace` prints one line; `git grep -n "worktree pause" -- dadaia_workspace/public/skills/dd-cli-library/SKILL.md` prints one line.

Tasks: 6 (5 sr, 1 jr). Each odd task is a RED and precedes its pair's even task; the three pairs are independent.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J8.T1 | sr | AC9.2 | `tests/cli/commands/test_migrate.py`, `tests/cli/commands/test_certify.py` | RED, integration. `migrate` on a registry already at the current stamp prints that stamp as its before and after, not `'2'` (fails today), and its `--help` names no "v1 to v2"; `test_certify.py` pins F-17's `schema_version 3` (fails today: 2) |
| J8.T2 | sr | AC9.2 | `dadaia_workspace/cli/commands/migrate.py`, `dadaia_workspace/features/migrate/state_v2.py`, `scripts/CONSUMER_VALIDATION_RECIPE.md` | REBUILD the stamp's spellings (Stamp bullet); owners `test_migrate.py`, `test_certify.py`; net lines at most 0 |
| J8.T3 | sr | AC9.2 | `tests/infrastructure/test_git_subprocess.py` | RED, integration. With `GIT_SSH_COMMAND` set to a stub ssh that records its argv, `reachable("ssh://…")` runs it with the user's own options and `-o BatchMode=yes` (fails today: the stub is never called); with `core.sshCommand` and no variable, the same; with neither, plain `ssh -o BatchMode=yes`; a reachable remote reads `True` |
| J8.T4 | sr | AC9.2 | `dadaia_workspace/infrastructure/git_subprocess.py` | REBUILD `reachable`'s environment (Reachability bullet); owner `test_git_subprocess.py` |
| J8.T5 | sr | AC9.2 | `tests/public/skills/dd_cli_library/test_skill_dist_writers.py` | RED, unit. The sentence of the skill that lists the `.dadaia/dist` writers names `worktree pause` and `worktree resume` (fails today); the file is new, in the folder that holds the skill's other test |
| J8.T6 | jr | AC9.2 | `dadaia_workspace/public/skills/dd-cli-library/SKILL.md` | REBUILD the sentence at `:28` (Dist writers bullet), shape 3 `refactor(bugs): cli-library-skill-omits-pause-as-a-dist-writer — REBUILD the dist-writer sentence: …`; owner `test_skill_dist_writers.py`; no other line of the skill changes |
