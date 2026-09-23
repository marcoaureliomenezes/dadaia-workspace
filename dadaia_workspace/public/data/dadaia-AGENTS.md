# .dadaia/AGENTS.md — Runtime Control Plane

## 1. Canonical folder law

- `.dadaia/` holds only the zones below plus `AGENTS.md` and `.gitignore`; anything else is slop.
- The table renders from `core/workspace_layout.DADAIA_ZONES` at `dadaia public stage`; TTL is seconds from mtime.
- Never create a new top-level `.dadaia/` directory — route into the zone owning that concern.

<!-- zones -->

## 2. Context, scope and races

- Resolution order: `DADAIA_CONTEXT` -> session binding -> the repo of the cwd (`dadaia context show --json`).
- `dadaia context bind <ctx> [--print-env]` is one verb — no mode, no release, no session state beyond the context; it is the sole context-memory-injection trigger. An exported `DADAIA_CONTEXT` IS the binding.
- Binding is optional; ADDITIVE writes need none. Scope = the bound context's main repo plus its associated repos; only `repos/<slug>/` is scope-judged.
- An out-of-scope write is BLOCKed with `fix: dadaia context bind <owner>`; an unbound session, an unregistered slug and a root path never are.
- Races surface, never block — no locks or leases; alert the operator only at zero ALIVE contexts.
- One harness session per checked-out tree; a parallel session's worktree is created before launch.
- The context surface is frozen: no new context verb, no new state file, no new session field.
- A single-repo context is the degenerate multi-repo case: the main repo is where `specs/` lives.

## 3. Git chokepoints

- The pre-push hook gates the `Bash` write path outside the gate's parsing, independent of any harness hook.
- It scans the pushed range only — published history is the baseline — and applies the specs canon only to a tree at the canonical stamp; a lower stamp is doctor drift, never a push block.
- `HOOKS-DRIFT-1`: an ALIVE repo's `.git/hooks/pre-push` differing from the shipped script; `fix: dadaia ci install-hook --force`.

## 4. Projections and law files

- Files in `agentic/manifest.json` are lib-originated projections; change them at the source under `dadaia_workspace/public/`, never in place.
- `AGENTS.md` law files are projected read-only and PROTECTED; only a human hand-edits a projected copy.
- Re-project with `dadaia public stage` then `dadaia public install`, then verify `[ok] public-privacy` with `dadaia public doctor`.

## 5. Doctor — the one scan and reaper

- `dadaia doctor` scans `workspace`, `specs` and `ledgers`; flags `--fix`, `--specs-dir`, `--context`, `--public-dir`, `--json`, `--expired-only`; exit 1 on an error finding.
- One finding per line, `<CODE> <verdict> <message>`; findings and the exit code are the whole report, no score line.
- The workspace scan covers the root, the harness dirs, the zones and every ALIVE repo's top level, plus an excluded name or nested `.dadaia/` at any depth.
- Slop and dead-repo leftovers are MOVED to `reaped/<YYYYMMDD>/<path>`, listed `WS-reaped-reaped`; nothing is deleted directly — an entry dies at its own TTL; move a mistakenly held one back before then.
- The reaper runs at SessionStart, on the PostToolUse throttle and on `--fix`.
