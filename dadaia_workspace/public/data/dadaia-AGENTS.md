# .dadaia/AGENTS.md — Runtime Control Plane

- Files in `agentic/manifest.json` are projections; change them at the package source; protection: root map §3.

## 1. Canonical folder law

- `.dadaia/` holds only the zones below plus `AGENTS.md` and `.gitignore`; anything else is slop.
- TTL is seconds from an entry's own mtime.
- A new top-level need goes into its owning zone.

<!-- zones -->

## 2. Context, scope and races

- Resolution order: the bind (a session with an id: its own record; none: a registered `DADAIA_CONTEXT`) -> the cwd repo (`.dadaia/.venv/bin/dadaia context show --json`); none -> bind, never borrow one.
- A root in `DADAIA_FENCED_ROOTS` is never resolved: no dadaia process or child acts on it.
- `.dadaia/.venv/bin/dadaia context bind <ctx>` is one verb, no mode or release; the memory-injection trigger (re-fired after compaction); the session id comes from the environment only; a subagent inherits its parent's session id and binding and never binds.
- Scope = the bound context's main and associated repos, judged under `repos/<slug>/` and `worktrees/<slug>/`; binding is optional, an ADDITIVE write needs none.
- An id-bearing session with no bind owns no repo; an unregistered slug and a root path are not scope-judged.
- Races are surfaced, not prevented; zero ALIVE -> alert the operator.
- One harness session per checked-out tree; parallel work: `worktrees/AGENTS.md`.

## 3. Git chokepoints

- The pre-push hook scans the pushed range only (published history is the baseline); the specs canon applies only to a tree at the canonical stamp, a tree whose `constitution.md` `specs_pattern_version` is lower passes the push, and `.dadaia/.venv/bin/dadaia doctor` prints its `specs init --context <ctx>` fix line.
- `HOOKS-DRIFT-1`: an ALIVE repo's `.git/hooks/pre-push` differing from the shipped script; run doctor's per-repo `fix:` line.

## 4. Projections and law files

- Re-project: `.dadaia/.venv/bin/dadaia public stage`, then `public install`, then `public doctor` shows `[ok] public-privacy`.

## 5. Doctor — the one scan and reaper

- `.dadaia/.venv/bin/dadaia doctor` scans `workspace`, `specs` and `ledgers`; exit 1 on an error finding.
- One finding per line, `<CODE> <verdict> <message>`; findings and exit code are the whole report.
- The workspace scan covers the root, the harness dirs, the zones and every ALIVE repo's top level, plus an excluded name or nested `.dadaia/` at any depth.
- Slop and dead-repo leftovers MOVE to `reaped/<YYYYMMDD>/<path>` (`WS-reaped-reaped`); nothing is deleted directly — an entry dies at its TTL; restore a wrongly held one before then with `mv .dadaia/reaped/<YYYYMMDD>/<path> <path>`.
- SessionStart reaps TTL-expired entries only; slop moves on `--fix`.
