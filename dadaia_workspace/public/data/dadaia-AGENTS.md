# .dadaia/AGENTS.md — Runtime Control Plane

Scope: this file governs `.dadaia/**`, the workspace runtime control plane.

`.dadaia/` contains generated projections, runtime state, reports, scripts,
hooks, temporary files, and local tooling. Treat it as operational state, not
product source.

## Subtree Rules

- `.dadaia/reports/AGENTS.md` governs human-readable reports.
- `.dadaia/handoff/AGENTS.md` governs machine-readable handoffs.
- `.dadaia/tmp/AGENTS.md` governs scratch files and evidence captures.
- `.dadaia/states/AGENTS.md` governs JSON state files.
- `.dadaia/agentic/manifest.json` identifies lib-originated projections.

Follow the nearest scoped `AGENTS.md` first.

## Write Policy

Do not hand-edit generated projections. If a file is listed in
`.dadaia/agentic/manifest.json`, edit the source under `dadaia_workspace/public/`
and run:

```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

Runtime JSON state should be changed through dadaia CLI commands or the
corresponding service code, not ad hoc text edits.

## Safe Areas

| Path | Rule |
|---|---|
| `.dadaia/reports/` | agent reports; must follow `.dadaia/reports/AGENTS.md` |
| `.dadaia/handoff/` | agent handoffs; must follow `.dadaia/handoff/AGENTS.md` |
| `.dadaia/tmp/` | disposable scratch/evidence; must follow `.dadaia/tmp/AGENTS.md` |
| `.dadaia/states/` | machine state; must follow `.dadaia/states/AGENTS.md` |
| `.dadaia/scripts/` | generated hook/runtime scripts; edit public source first |
| `.dadaia/agentic/` | staged public assets; generated, do not edit directly |
| `.dadaia/.venv/` | managed Python environment; do not edit manually |

## Validation

After changing runtime-control behavior, run:

```bash
dadaia public doctor
dadaia specs doctor
```

If doctor reports drift, fix the public source or state owner. Do not patch the
projection in place.
