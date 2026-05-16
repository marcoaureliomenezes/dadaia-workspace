# /dadaia-workspace-doctor

Diagnose and repair the dadaia workspace runtime using the `dadaia-workspace-doctor` skill.

## Usage

```
/dadaia-workspace-doctor
/dadaia-workspace-doctor drift        → check package/staging/runtime asset drift only
/dadaia-workspace-doctor schema       → check JSON schema migration only
/dadaia-workspace-doctor fix          → run all checks and apply automatic repairs
```

## What it does

1. **Phase 0** — Locates the workspace root and library installation
2. **Phase 1** — Compares `dadaia_workspace/public/`, `.dadaia/agentic/`, and runtime projections; reports drift
3. **Phase 2** — Checks `.dadaia/states/*.json` schema against current Python dataclasses; guides migration if stale
4. **Phase 3** — Writes a diagnostic report to `.dadaia/reports/specs-sdd-review/doctor-<date>.md`

## When to use

- After updating the `dadaia-workspace` library
- When `dadaia context show --json` returns unexpected fields
- When `dadaia doctor` reports issues that need AI-assisted migration guidance
- When runtime projection assets look different from what `dadaia_workspace/public/` defines

## CLI equivalent

```bash
dadaia doctor           # check only
dadaia doctor --fix     # check + repair
dadaia public doctor    # check public asset drift
dadaia public stage
dadaia public install --target all --force
```
