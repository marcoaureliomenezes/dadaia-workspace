# .dadaia/AGENTS.md — Runtime Control Plane

## 1. Canonical folder law

- `.dadaia/` holds only the zones below plus `AGENTS.md` and `.gitignore`; anything else is slop.
- The table renders from `core/workspace_layout.DADAIA_ZONES` at `public stage`; TTL is seconds from an entry's own mtime.
- Never create a new top-level `.dadaia/` directory — route into the zone owning that concern.

<!-- zones -->

## 2. Context, scope and races

- Resolution order: the bind (a session with an id: its own record; none: a registered `DADAIA_CONTEXT`) -> the cwd repo (`.dadaia/.venv/bin/dadaia context show --json`); none -> bind, never borrow one.
- A root in `DADAIA_FENCED_ROOTS` is never resolved: no dadaia process or child acts on it; the suite, the preflight and every mutating probe set it.
- `.dadaia/.venv/bin/dadaia context bind <ctx> [--print-env]` is one verb — no mode, no release, no session state beyond the context; the sole memory-injection trigger.
- Binding is optional; ADDITIVE writes need none. Scope = the bound context's main repo plus its associated repos; only `repos/<slug>/` is scope-judged.
- An out-of-scope file-tool write is BLOCKed with `fix: .dadaia/.venv/bin/dadaia context bind <owner>`; an unbound session, an unregistered slug and a root path never are.
- Races surface, never block — no locks or leases; zero ALIVE -> alert the operator.
- One harness session per checked-out tree; a parallel session gets its worktree before launch.
- Frozen context surface (ADR 0027): `context create` absorbs clone, hook, ALIVE, never binds; no new state file or session field.

## 3. Git chokepoints

- The pre-push hook judges what a push publishes, whichever tool wrote it; the gate never judges a Bash write (root map §3).
- It scans the pushed range only — published history is the baseline — and applies the specs canon only to a tree at the canonical stamp; a lower stamp is doctor drift, never a push block.
- `HOOKS-DRIFT-1`: an ALIVE repo's `.git/hooks/pre-push` differing from the shipped script; run doctor's per-repo `fix:` line.

## 4. Projections and law files

- Files in `agentic/manifest.json` are lib-originated projections; change them at the source under `dadaia_workspace/public/`, never in place.
- Every projected file (the install ledger records it) is PROTECTED; only a human hand-edits a projected copy.
- Re-project: `.dadaia/.venv/bin/dadaia public stage`, then `public install`, then `public doctor` shows `[ok] public-privacy`.

## 5. Doctor — the one scan and reaper

- `.dadaia/.venv/bin/dadaia doctor` scans `workspace`, `specs` and `ledgers`; exit 1 on an error finding.
- One finding per line, `<CODE> <verdict> <message>`; findings and the exit code are the whole report, no score line.
- The workspace scan covers the root, the harness dirs, the zones and every ALIVE repo's top level, plus an excluded name or nested `.dadaia/` at any depth.
- Slop and dead-repo leftovers are MOVED to `reaped/<YYYYMMDD>/<path>`, listed `WS-reaped-reaped`; nothing is deleted directly — an entry dies at its own TTL; move a mistakenly held one back before then.
- SessionStart reaps TTL-expired entries only; slop moves on `--fix`; never on a tool call.
