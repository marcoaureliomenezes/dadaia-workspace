# .dadaia/AGENTS.md — Runtime Control Plane

Scope: this file governs `.dadaia/**`, the workspace runtime control plane —
generated projections, runtime state, machine/human outputs, and disposable
scratch. Treat it as operational state, **not** product source.

## Canonical folder law

`.dadaia/` may contain **only** the canonical subdirectories in the table below,
plus dotfiles at the `.dadaia` level (e.g. `.gitkeep`). **Every other directory
is slop and is forbidden** — the ROOT-4 doctor invariant blocks unknown
subdirs, and `dadaia reconcile` quarantines known-legacy ones into
`.dadaia/tmp/legacy-quarantine/` (moved, never deleted). Do not create a new
top-level `.dadaia/` directory to park anything; route it into the canonical
zone that owns that concern, or under `.dadaia/tmp/<agent>/<YYYYMMDD>/`.

Each canonical folder has ONE architectural purpose. If a file does not fit an
existing purpose, it does not belong in `.dadaia/` at all.

| Folder | Architectural purpose | Class | Editable by hand? |
|---|---|---|---|
| `agentic/` | Staged lib-originated public assets + `manifest.json` — the projection source-of-truth that tracks every generated file. | projection | No — regen via `dadaia public install` |
| `hooks/` | Projected Python governance hook entrypoints (`pre_gate`, `sdd_post_gate`, `ctx_inject`) the harness runs pre/post tool use. | projection | No — lib-originated |
| `scripts/` | Projected runtime/git-hook scripts (pre-push CI + security gate, memory-atom lint). | projection | No — edit public source |
| `mcps/` | Per-MCP-server working directories (`mcps/<server>/`). All MCP runtime state lives here — never at the root. | runtime | Server-managed |
| `references/` | Operator-placed reference clones (`references/<clone>/`), outside the context lifecycle — never resolved, bound, alived, deaded or GC'd, and never flagged by the doctor. | operator-owned | Operator-managed |
| `states/` | Machine-readable runtime state JSON: `spec_contexts`, `presence/`, `server_registry`, model policies, `root_exceptions.txt`. | state | No — change via `dadaia` CLI / service code |
| `sessions/` | Per-session identity + bind records (one file per session id). PROTECTED path class — the gate fails closed here. | state | No — written by bind/gate |
| `handoff/` | Machine-readable agent handoff JSON, `handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`. See `handoff/AGENTS.md`. | output | Append-only, schema-validated |
| `reports/` | Human-readable HTML reports, `reports/<context>/<agent>/<UTC>-<slug>.html`. See `reports/AGENTS.md`. | output | Follow the scoped rule |
| `academy/` | Agent study / mastery area — durable field notes and validation ledgers an agent keeps for itself. | output | Agent-owned |
| `tmp/` | Disposable scratch + evidence captures, `tmp/<agent>/<YYYYMMDD>/`. GC'd; never load-bearing. See `tmp/AGENTS.md`. | ephemeral | Yes — disposable |
| `logs/` | Telemetry / event logs (e.g. hook latency). Disposable, rotatable. | ephemeral | Yes — disposable |
| `runs/` | Workflow run transcripts (`runs/lifecycle/`). Disposable evidence of past workflow executions. | ephemeral | Yes — disposable |
| `dev-report/` | Generated developer diagnostic reports (self-check output). Disposable. | ephemeral | Yes — disposable |
| `dist/` | Built artifacts (wheels) and workspace exports produced locally. | artifact | Yes — but prune stale builds |
| `runtime/` | Long-lived local runtime working area for tooling that needs a stable path (not scratch). | runtime | Tool-managed |
| `.venv/` | Managed workspace Python environment. | managed | No — re-bootstrap only |
| `.cache/` | Redirected tool caches (ruff `cache-dir`, coverage `data_file`) — kept OUT of any repo. | managed | Yes — disposable |

There is no "misc", "assets", "imgs", or "bridge" folder. Those are junk
drawers; put images/evidence under `tmp/<agent>/<date>/`, MCP working state
under `mcps/<server>/`, and durable notes under `academy/`.

## Scoped subtree rules — follow the nearest first

- `reports/AGENTS.md` — human-readable reports.
- `handoff/AGENTS.md` — machine-readable handoffs.
- `tmp/AGENTS.md` — scratch files and evidence captures.
- `states/AGENTS.md` — JSON state files.
- `agentic/manifest.json` — the lib-originated projection inventory.

## Write policy

Do not hand-edit generated projections. If a file is listed in
`agentic/manifest.json`, edit the source under `dadaia_workspace/public/` and run:

```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

Runtime JSON state changes through `dadaia` CLI commands or the owning service
code — never ad hoc text edits.

## Hygiene

- Never park a loose file or a new directory at the `.dadaia/` root. If you
  reach for a location that is not a canonical folder above, stop — it is slop.
- `tmp/`, `logs/`, `runs/`, `dev-report/` are disposable: safe to clear anytime.
  Everything else is either regenerable (projections) or CLI-owned state.
- Stale builds in `dist/` and expired `sessions/` are GC targets; the doctor and
  `dadaia clean` reclaim them — do not let them accumulate.

## Validation

After changing runtime-control behavior:

```bash
dadaia public doctor
dadaia specs doctor
```

If doctor reports drift or a ROOT-4 unknown subdir, fix the public source or the
state owner and quarantine the stray dir — never patch the projection in place,
never rubber-stamp a new folder into the canonical set to silence the check.
