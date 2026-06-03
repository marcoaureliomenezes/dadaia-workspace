---
name: tmp-file-guardrail
description: All agent-generated ephemeral files must land in .dadaia/tmp/. Workspace root and other directories are off-limits.
always_on: true
---

# tmp-file-guardrail

This rule is always active. All agent-generated temp files MUST go to `.dadaia/tmp/<agent-name>/<YYYYMMDD>/`. Never at workspace root or in `repos/`, `specs/`, `.claude/`, or `.dadaia/agentic/`.

## Mandatory landing zone

```
.dadaia/tmp/<agent-name>/<YYYYMMDD>/
```

Create with `mkdir -p` if the directory does not exist.

## What counts as a temp file

| File type | Examples | Must go to `.dadaia/tmp/` |
|---|---|---|
| Playwright screenshots | `*.png`, `*.jpg` | Always |
| DOM snapshots | `*-dom.html` | Always |
| Intermediate query results | `*.json`, `*.arrow`, `*.parquet`, `*.csv` | Always |
| Exported manifests | `export-manifest.json`, `*.zip` | Always |
| Agent-generated scripts (exploratory) | `pw_*.js`, `check_*.py` | Always |
| API response captures | `query-post-response.json`, `*.stream` | Always |
| Discovery / draft notes | `draft_snapshot.md`, `prompt.md` | Always |

## Workspace root whitelist

| File | Origin |
|---|---|
| `AGENTS.md` | lib-originated |
| `CLAUDE.md` | operator-authored |
| `opencode.json` | lib-originated |
| `.mcp.json` | operator-authored |
| `.dadaia/` | workspace state directory |
| `repos/` | spec context project repos |
| `scripts/` | operator-authored utility scripts |

**Nothing else belongs at root.**

## Enforcement

Before writing a file outside `.dadaia/tmp/` that matches the temp-file criteria above, STOP and redirect to `.dadaia/tmp/<agent-name>/<YYYYMMDD>/`. Report any stray temp files found at root or in forbidden locations — do not silently ignore workspace pollution. Reports go to `.dadaia/reports/<ctx>/<agent>/`, never to `.dadaia/tmp/`.
