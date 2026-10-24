# .dadaia/AGENTS.md — Runtime Control Plane

- Files in `agentic/manifest.json` are projections; change them at the package source; protection: root map (What is enforced).

## 1. Canonical folder law

- `.dadaia/` holds only the zones below plus `AGENTS.md` and `.gitignore`; anything else is slop.
- TTL is seconds from an entry's own mtime.
- A new top-level need goes into its owning zone.

<!-- zones -->

## 2. Context, scope and races

- Resolution order: the bind (a session with an id: its own record; none: a registered `DADAIA_CONTEXT`) -> the cwd repo (`.dadaia/.venv/bin/dadaia context show --json`); none -> bind, never borrow one.
- Automatic workspace and root resolution skips every root in `DADAIA_FENCED_ROOTS`; an explicitly named target such as a ledger script's `--specs` path is resolved independently.
- `.dadaia/.venv/bin/dadaia context bind <ctx>` binds; the ctx-inject hook then injects memory (`dd-spec-navigator` Phase 2); the CLI verbs read the session id from the environment, and the hooks also take the hook payload's id where the harness's registry row names a session variable; a subagent inherits its parent's session id and binding and never binds.
- Scope = the bound context's main and associated repos, judged under `repos/<slug>/` and `worktrees/<slug>/`; a write inside a tree git linked from a registered repo is in scope whatever the bind; binding is optional, an ADDITIVE write needs none.
- An id-bearing session with no bind owns no repo; an unregistered slug and a root path are not scope-judged.
- Races are surfaced, not prevented; zero ALIVE -> alert the operator.
- One harness session per checked-out tree; parallel work: `worktrees/AGENTS.md`.

## 3. Git chokepoints

- The pre-push hook admits its pushable branch shapes (`dd-gitflow-default`, The branch contract). It also admits the initial ref for either PR-only branch when origin has no Gitflow branch, or when the ref publishes no new objects; it refuses a non-canon `specs/` path or a denylisted secret. It scans the pushed range only (published history is the baseline); the specs canon applies only to a tree at the canonical stamp, a tree whose `constitution.md` `specs_pattern_version` is lower passes the push, and `.dadaia/.venv/bin/dadaia doctor` prints its `specs init --context <ctx>` fix line.
- The reference-transaction ref gate (create and move of `wt/*` and work branches) is specified in `worktrees/AGENTS.md` (top).
- `HOOKS-DRIFT-1`: an ALIVE repo's installed `pre-push` or `reference-transaction` hook differing from the shipped script; run doctor's per-repo `fix:` line.

## 4. Projections and law files

- Re-project: `.dadaia/.venv/bin/dadaia public install`, then `public doctor` shows `[ok] public-privacy`.

## 5. Doctor — the one scan and reaper

- `.dadaia/.venv/bin/dadaia doctor` scans `workspace`, `specs` and `ledgers`; exit 1 on an error finding.
- One finding per line, `<CODE> <verdict> <message>`; findings and exit code are the whole report.
- The workspace scan covers the root, the harness dirs, the zones and every ALIVE repo's top level, plus an excluded name or nested `.dadaia/` at any depth.
- Slop and dead-repo leftovers MOVE to `reaped/<YYYYMMDD>/<path>` (`WS-reaped-reaped`); nothing is deleted directly — an entry dies at its TTL; restore a wrongly held one before then with `mv .dadaia/reaped/<YYYYMMDD>/<path> <path>`.
- SessionStart reaps TTL-expired entries only; slop moves on `--fix`.
