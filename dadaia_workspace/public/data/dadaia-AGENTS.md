# .dadaia/AGENTS.md — Runtime Control Plane

Scope: this file governs `.dadaia/**`, the workspace runtime control plane.
Treat it as operational state, not product source.

## 1. Canonical folder law

- `.dadaia/` may contain only the zones below, plus `AGENTS.md` and `.gitignore`; anything else is slop (`DADAIA.md` §8.5).
- The table is rendered from `core/workspace_layout.DADAIA_ZONES` at `dadaia public stage`; TTL is seconds by mtime before `dadaia doctor` expires an entry, `never` = not clock-expired.
- Never create a new top-level `.dadaia/` directory — route into the zone that owns that concern; a misfit file does not belong in `.dadaia/` at all.

<!-- zones -->

- Evidence goes under `tmp/<agent>/<date>/`, MCP working state under `mcps/<server>/`; HTML reports live in the repo (`DADAIA.md` §5.2).

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

- `dadaia doctor` is the one scan and reaper: a loose file or unknown directory at the `.dadaia/` root is a `WS-dadaia-slop` finding — route it into the zone that owns it.
- SessionStart reaps only expired entries; slop dies only by an explicit operator `dadaia doctor --fix`.

## 5. Validation

```bash
dadaia doctor
dadaia public doctor
dadaia specs doctor
```

- On drift or a `WS-*-slop` finding: fix the public source or the state owner; `dadaia doctor --fix` deletes only what its dry run listed.
- Never patch the projection in place; never rubber-stamp a new folder into the canonical set to silence the check.
