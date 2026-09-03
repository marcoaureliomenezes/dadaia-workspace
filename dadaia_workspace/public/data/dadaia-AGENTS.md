# .dadaia/AGENTS.md — Runtime Control Plane

Scope: this file governs `.dadaia/**`, the workspace runtime control plane.
Treat it as operational state, not product source.

## 1. Canonical folder law

- `.dadaia/` may contain only the canonical subdirectories below, plus dotfiles (e.g. `.gitignore`).
- Every other directory is forbidden (`DADAIA.md` §7.6) — the ROOT-4 doctor invariant blocks unknown subdirs.
- `dadaia reconcile` quarantines known-legacy dirs into `.dadaia/tmp/legacy-quarantine/` (moved, never deleted).
- Never create a new top-level `.dadaia/` directory — route into the canonical zone that owns that concern.
- Each canonical folder has ONE architectural purpose; a misfit file does not belong in `.dadaia/` at all.

| Folder | Architectural purpose | Class | Editable by hand? |
|---|---|---|---|
| `agentic/` | Staged lib-originated public assets + `manifest.json` | projection | No — regen via `dadaia public install` |
| `hooks/` | Projected Python governance hook entrypoints | projection | No — lib-originated |
| `scripts/` | Projected runtime/git-hook scripts | projection | No — edit public source |
| `mcps/` | Per-MCP-server working directories (`mcps/<server>/`) | runtime | Server-managed |
| `references/` | Operator-placed reference clones, outside the context lifecycle | operator-owned | Operator-managed |
| `states/` | Machine-readable runtime state JSON | state | No — change via `dadaia` CLI / service code |
| `sessions/` | Per-session identity + bind records; PROTECTED, gate fails closed | state | No — written by bind/gate |
| `handoff/` | Machine-readable agent handoff JSON (`handoff/AGENTS.md`) | output | Append-only, schema-validated |
| `reports/` | Human-readable HTML reports (`reports/AGENTS.md`) | output | Follow the scoped rule |
| `academy/` | Agent study / mastery area — durable field notes and validation ledgers | output | Agent-owned |
| `tmp/` | Disposable scratch + evidence captures (`tmp/AGENTS.md`) | ephemeral | Yes — disposable |
| `logs/` | Telemetry / event logs (e.g. hook latency) | ephemeral | Yes — disposable |
| `runs/` | Workflow run transcripts (`runs/lifecycle/`) | ephemeral | Yes — disposable |
| `dev-report/` | Generated developer diagnostic reports (self-check output) | ephemeral | Yes — disposable |
| `dist/` | Built artifacts (wheels) and local workspace exports | artifact | Yes — but prune stale builds |
| `runtime/` | Long-lived local runtime working area for tooling needing a stable path | runtime | Tool-managed |
| `.venv/` | Managed workspace Python environment | managed | No — re-bootstrap only |
| `.cache/` | Redirected tool caches (kept OUT of any repo) | managed | Yes — disposable |

- There is no "misc", "assets", "imgs", or "bridge" folder — those are junk drawers.
- Put images/evidence under `tmp/<agent>/<date>/`, MCP working state under `mcps/<server>/`, durable notes under `academy/`.

## 2. Scoped subtree rules — follow the nearest first

- `reports/AGENTS.md` — human-readable reports.
- `handoff/AGENTS.md` — machine-readable handoffs.
- `tmp/AGENTS.md` — scratch files and evidence captures.
- `states/AGENTS.md` — JSON state files.
- `agentic/manifest.json` — the lib-originated projection inventory.

## 3. Write policy

- Do not hand-edit generated projections.
- If a file is listed in `agentic/manifest.json`, edit the source under `dadaia_workspace/public/` and run:

```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

- Runtime JSON state changes through `dadaia` CLI commands or the owning service code — never ad hoc text edits.

## 4. Hygiene

- A loose file or a new directory at the `.dadaia/` root has no canonical home (`DADAIA.md` §7.6) — route it into the zone that owns it.
- `tmp/`, `logs/`, `runs/`, `dev-report/` are disposable, safe to clear anytime.
- Everything else is either regenerable (projections) or CLI-owned state.
- Stale builds in `dist/` and expired `sessions/` are GC targets — doctor and `dadaia clean` reclaim them.

## 5. Validation

```bash
dadaia public doctor
dadaia specs doctor
```

- On drift or a ROOT-4 unknown subdir: fix the public source or the state owner, quarantine the stray dir.
- Never patch the projection in place; never rubber-stamp a new folder into the canonical set to silence the check.
