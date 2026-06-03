# tmp-file-guardrail

This rule is always active. It applies to every agent operating in this workspace.

## Purpose

Agents that create ephemeral files (Playwright screenshots, intermediate JSONs, exported
manifests, downloaded data, generated scripts, exploration artefacts) MUST place them
inside `.dadaia/tmp/`. The workspace root and all non-designated directories are **off-limits**
for agent-generated temp files. Violation is workspace pollution.

## Mandatory landing zone

```
.dadaia/tmp/<agent-name>/<YYYYMMDD-or-session-id>/
```

Examples:
```
.dadaia/tmp/qa-engineer/20260523/dashboard-overview.png
.dadaia/tmp/domain-specialist/20260522/query-result-327.json
.dadaia/tmp/design-specialist/20260523/panel-capture-01.png
.dadaia/tmp/researcher/20260521/export-manifest.json
```

If the date/session sub-directory does not exist, create it with `mkdir -p` before writing.

## What counts as a temp file

| File type | Examples | Must go to `.dadaia/tmp/` |
|---|---|---|
| Playwright screenshots | `*.png`, `*.jpg` | ✅ Always |
| DOM snapshots | `*-dom.html` | ✅ Always |
| Intermediate query results | `*.json`, `*.arrow`, `*.parquet`, `*.csv` | ✅ Always |
| Exported manifests | `export-manifest.json`, `*.zip` | ✅ Always |
| Agent-generated scripts (exploratory) | `pw_*.js`, `check_*.py` | ✅ Always |
| API response captures | `query-post-response.json`, `*.vndapachearrowstream` | ✅ Always |
| Discovery / draft notes | `draft_snapshot.md`, `prompt.md` | ✅ Always |

## What belongs at workspace root (whitelist)

Only these files are permitted at the workspace root (`/`):

| File | Origin |
|---|---|
| `AGENTS.md` | lib-originated (dadaia public install) |
| `CLAUDE.md` | operator-authored |
| `opencode.json` | lib-originated (dadaia public install) |
| `.mcp.json` | operator-authored |
| `.dadaia/` | workspace state directory |
| `repos/` | spec context project repos |
| `scripts/` | operator-authored utility scripts |

**Never create any other file directly at the workspace root.**

## Forbidden locations (beyond root)

Do NOT dump temp files in:
- `repos/<any-repo>/` root
- `.claude/` or `.dadaia/agentic/` (lib-originated projections — read-only)
- `specs/` (SDD gate enforced — only product-engineer + SDD lifecycle writes)

## Cleanup

`.dadaia/tmp/` is ephemeral. Agents may delete their own sub-directories after their task
completes. The operator runs `rm -rf .dadaia/tmp/*` to purge all temp artefacts between
sessions. Nothing inside `.dadaia/tmp/` should be considered persistent or reportable —
reports go to `.dadaia/reports/<ctx>/<agent>/`, never to `.dadaia/tmp/`.

## Enforcement

If you are about to write a file outside `.dadaia/tmp/` that matches the temp-file
criteria above, STOP and redirect to `.dadaia/tmp/<agent-name>/<date>/`. If your current
tool call would place the file at root or in a forbidden location, do not issue the call —
rewrite the path first.

When you observe stray temp files at the workspace root or in forbidden locations, report
them to the operator and list them for cleanup. Do not silently ignore workspace pollution.
