# .dadaia/AGENTS.md — Runtime Control Plane

Scope: this file governs `.dadaia/**`, the workspace runtime control plane.
Treat it as operational state, not product source.

## 1. Canonical folder law

- `.dadaia/` may contain only the zones below, plus `AGENTS.md` and `.gitignore`.
- Every other directory is forbidden (`DADAIA.md` §7.6) — the ROOT-4 doctor invariant blocks unknown subdirs.
- `dadaia reconcile` quarantines known-legacy dirs into `.dadaia/tmp/legacy-quarantine/` (moved, never deleted).
- Never create a new top-level `.dadaia/` directory — route into the canonical zone that owns that concern.
- Each canonical folder has ONE architectural purpose; a misfit file does not belong in `.dadaia/` at all.

The table is rendered from `core/workspace_layout.py` at `dadaia public stage`. TTL is
seconds by mtime before `dadaia doctor` expires an entry; `never` = not clock-expired.

<!-- zones -->

- There is no "misc", "assets", "imgs", or "bridge" folder — those are junk drawers.
- Put images/evidence under `tmp/<agent>/<date>/`, MCP working state under `mcps/<server>/`.

## 2. Scoped subtree rules — follow the nearest first

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
- Everything else is either regenerable (projections) or CLI-owned state.

## 5. Validation

```bash
dadaia public doctor
dadaia specs doctor
```

- On drift or a ROOT-4 unknown subdir: fix the public source or the state owner, quarantine the stray dir.
- Never patch the projection in place; never rubber-stamp a new folder into the canonical set to silence the check.
