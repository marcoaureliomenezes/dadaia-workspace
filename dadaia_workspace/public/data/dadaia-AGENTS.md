# .dadaia/AGENTS.md — Runtime Control Plane

Scope: `.dadaia/**` and the deterministic enforcement riding on it.

## 1. Canonical folder law

- `.dadaia/` may contain only the zones below, plus `AGENTS.md` and `.gitignore`; anything else is slop.
- The table is rendered from `core/workspace_layout.DADAIA_ZONES` at `dadaia public stage`; TTL is seconds by mtime before `dadaia doctor` expires an entry.
- Never create a new top-level `.dadaia/` directory — route into the zone that owns that concern; a misfit file does not belong in `.dadaia/` at all.

<!-- zones -->

## 2. Scoped subtree rules — follow the nearest first

- `handoff/AGENTS.md` — machine-readable handoffs.
- `tmp/AGENTS.md` — scratch files and evidence captures.
- `states/AGENTS.md` — JSON state files.

## 3. Context, scope and races

- Resolution order: `DADAIA_CONTEXT` -> session binding -> the repo of the cwd; inspect with `dadaia context show --json`.
- `dadaia context bind <ctx> [--print-env]` is one verb: no mode, no release, no session state beyond the context — it refreshes the session and is the sole context-memory-injection trigger.
- A plain shell's exported `DADAIA_CONTEXT` env var IS the binding; binding is optional and ADDITIVE writes need none.
- Scope = the bound context's main repo plus its associated repos; only `repos/<slug>/` is scope-judged.
- An out-of-scope write is BLOCKed with `fix: dadaia context bind <owner>`; an unbound session, an unregistered slug and a workspace-root path are never scope-blocked.
- Races surface, never block — no locks, leases or ownership blocks; alert the operator only at zero ALIVE contexts.
- One harness session per checked-out tree; a parallel session's worktree is created before launch.
- The context surface is frozen: no new context verb, no new state file, no new session field.
- A single-repo context is the degenerate case of multi-repo: the main repo is the one where `specs/` lives, the associated repos are the others the context owns.

## 4. Git chokepoints

- The pre-push git hook gates the `Bash` write path, outside the gate's own parsing, independent of any harness hook.
- pre-push allows `feature/*` after CI preflight and a valid name; it refuses a direct `develop`/`main` push or a non-canon `specs/` path the pushed range introduces or rewrites.
- It scans the pushed range only: published history is the baseline and is never rescanned.
- It applies the specs canon only to a `specs/` tree stamped at the canonical pattern; a lower stamp is doctor drift, never a push block.
- `HOOKS-DRIFT-1`: an ALIVE repo's installed `.git/hooks/pre-push` byte-differing from the shipped script; `fix: dadaia ci install-hook --force`.

## 5. Write policy — projections and law files

- Files listed in `agentic/manifest.json` are lib-originated projections; change them at the source under `dadaia_workspace/public/`, never in place.
- `AGENTS.md` law files are projected read-only and PROTECTED; only a human hand-edits a projected copy.
- Re-project, then verify `[ok] public-privacy`:

```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```


## 6. Doctor — the one scan and reaper

- `dadaia doctor` scans `workspace`, `specs` and `ledgers`; flags `--fix`, `--specs-dir`, `--context`, `--public-dir`, `--json`, `--expired-only`; exit 1 on any error-class finding.
- One finding per line, `<CODE> <verdict> <message>`; findings and the exit code are the whole report — no score line.
- The workspace scan covers the root, the harness dirs, the `.dadaia/` zones and the top of every ALIVE registered repo, plus an excluded name or a nested `.dadaia/` at any depth in a repo.
- Slop and dead-repo leftovers are MOVED to `reaped/<YYYYMMDD>/<workspace-relative-path>` and listed `WS-reaped-reaped`; nothing is deleted directly — an entry dies at its own TTL.
- It runs at SessionStart, on the PostToolUse throttle, and on `dadaia doctor --fix`; recover a mistakenly held entry by moving it back before its TTL.
