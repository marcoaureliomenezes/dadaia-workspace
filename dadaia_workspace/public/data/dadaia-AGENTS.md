# .dadaia/AGENTS.md — Runtime Control Plane

## 1. Canonical folder law

- `.dadaia/` holds only the zones below plus `AGENTS.md` and `.gitignore`; anything else is slop.
- The table renders from `core/workspace_layout.DADAIA_ZONES` at `public stage`; TTL is seconds from an entry's own mtime.
- Never create a new top-level `.dadaia/` directory; use the owning zone.

<!-- zones -->

## 2. Context, scope and races

- Resolution order: the bind (a session with an id: its own record; none: a registered `DADAIA_CONTEXT`) -> the cwd repo (`.dadaia/.venv/bin/dadaia context show --json`); none -> bind, never borrow one.
- A root in `DADAIA_FENCED_ROOTS` is never resolved: no dadaia process or child acts on it; the suite and mutating probes set it.
- `.dadaia/.venv/bin/dadaia context bind <ctx>` is one verb, no mode or release; the sole memory-injection trigger; the session id comes from the environment only, so a nested session shares its parent's bind.
- Scope = the bound context's main and associated repos, judged under `repos/<slug>/` and `worktrees/<slug>/`; binding is optional, an ADDITIVE write needs none.
- An out-of-scope file-tool write is BLOCKed with `fix: .dadaia/.venv/bin/dadaia context bind <owner>`; an unbound session with an id owns no repo; an unregistered slug and a root path are never scope-judged.
- Races surface, never block (no locks); zero ALIVE -> alert the operator.
- One harness session per checked-out tree; parallel work: `worktrees/AGENTS.md`.
- Frozen context surface (ADR 0027): `context create` clones, hooks, ALIVEs, never binds; no new state file or session field.

## 3. Git chokepoints

- The pre-push hook judges what a push publishes, whichever tool wrote it.
- It scans the pushed range only (published history is the baseline); the specs canon applies only to a tree at the canonical stamp, a lower one is doctor drift, never a push block.
- `HOOKS-DRIFT-1`: an ALIVE repo's `.git/hooks/pre-push` differing from the shipped script; run doctor's per-repo `fix:` line.

## 4. Projections and law files

- Files in `agentic/manifest.json` are projections; change them at their `dadaia_workspace/public/` source, never in place.
- Every projected file (in the install ledger) is PROTECTED; only a human hand-edits one.
- Re-project: `.dadaia/.venv/bin/dadaia public stage`, then `public install`, then `public doctor` shows `[ok] public-privacy`.

## 5. Doctor — the one scan and reaper

- `.dadaia/.venv/bin/dadaia doctor` scans `workspace`, `specs` and `ledgers`; exit 1 on an error finding.
- One finding per line, `<CODE> <verdict> <message>`; findings and exit code are the whole report.
- The workspace scan covers the root, the harness dirs, the zones and every ALIVE repo's top level, plus an excluded name or nested `.dadaia/` at any depth.
- Slop and dead-repo leftovers MOVE to `reaped/<YYYYMMDD>/<path>` (`WS-reaped-reaped`); nothing is deleted directly — an entry dies at its TTL; move a wrongly held one back before then.
- SessionStart reaps TTL-expired entries only; slop moves on `--fix`; never on a tool call.
