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

The workspace root may contain **only** the following entries:

| Entry | Type | Origin |
|-------|------|--------|
| `.agents/` | dir | lib-originated projection |
| `.claude/` | dir | lib-originated projection |
| `.codex/` | dir | lib-originated projection |
| `.dadaia/` | dir | workspace state directory |
| `.opencode/` | dir | lib-originated projection |
| `repos/` | dir | spec context project repos |
| `AGENTS.md` | file | lib-originated (dadaia public install) |
| `CLAUDE.md` | file | Claude Code bridge importing `@AGENTS.md` (constitution §3) |
| `prompt.md` | file | optional operator long-prompt file (constitution §3) |

`CLAUDE.md` is required: Claude Code does not read `AGENTS.md` natively, so a root
`CLAUDE.md` containing `@AGENTS.md` is the authorized import bridge that loads the
workspace law. `prompt.md` is an optional operator-authored long-prompt file.

**Nothing else belongs at root.** Files such as `opencode.json`, `.mcp.json`,
and `scripts/` are NOT default-whitelisted. If a specific tool genuinely requires
one of these at root, it must be added as a documented exception in
`.dadaia/states/root_exceptions.txt` (one glob per line) after operator approval.

**Operator exception:** any file or directory created by the human operator is always
allowed and must never be auto-deleted (e.g. `prompt.md`, `sessions-tab-1280.png`).

This whitelist is enforced for file-write tools by the
`dadaia_workspace.hooks.root_whitelist` PreToolUse hook (Python). `Bash`-side writes are
outside the hook's envelope (Decision D-2) and are governed by this rule as discipline.

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

## Discipline

The temp-file landing zone is **agent discipline, not hook-enforced**: no hook inspects
where a temp file lands (only new top-level root entries are deterministically blocked,
per the root-whitelist hook above). Before writing a file outside `.dadaia/tmp/` that
matches the temp-file criteria above, STOP and redirect to
`.dadaia/tmp/<agent-name>/<YYYYMMDD>/`. Report any stray temp files found at root or in
forbidden locations — do not silently ignore workspace pollution. Reports go to
`.dadaia/reports/<ctx>/<agent>/`, never to `.dadaia/tmp/`.
