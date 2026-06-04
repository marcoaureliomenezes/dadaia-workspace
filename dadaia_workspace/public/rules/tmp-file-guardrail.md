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

## No cache/state dirs inside repos

No repo may contain cache, state, or artifact directories in its working tree. This is a zero-tolerance policy.

**Unconditionally forbidden inside any repo:**
`.dadaia/`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.hypothesis/`, `.ruff_cache/`, `test-results/`, `playwright-report/`, `coverage/`, `.coverage`.

**`.dadaia/` is workspace-level only** — it lives at the workspace root. Creating `.dadaia/` inside a repo corrupts workspace-vs-repo boundary detection and is a hard violation.

Tools must run with caching disabled or redirected outside the repo:
- pytest: `-p no:cacheprovider`
- mypy: `incremental = false`
- hypothesis: `database = None`
- ruff: `--no-cache`
- Playwright: `outputDir` → `.dadaia/tmp/<agent>/<date>/`

Gitignoring these dirs is defence-in-depth only — gitignore is not a licence to create them. See the `## Repo cleanliness` section in the root `AGENTS.md` for the full policy.

## Enforcement

Before writing a file outside `.dadaia/tmp/` that matches the temp-file criteria above, STOP and redirect to `.dadaia/tmp/<agent-name>/<YYYYMMDD>/`. Report any stray temp files found at root or in forbidden locations — do not silently ignore workspace pollution. Reports go to `.dadaia/reports/<ctx>/<agent>/`, never to `.dadaia/tmp/`.
