---
title: configure-hook-writes-malformed-duplicate-userpromptsubmit
severity: High
opened: 2026-06-07
session_id: null
status: Closed
---

# Bug: configure-hook-writes-malformed-duplicate-userpromptsubmit

## Description

`WorkspaceService._configure_hook` appends a **malformed, duplicate**
`UserPromptSubmit` hook entry to `.claude/settings.json`, producing a settings
file that fails Claude Code's settings schema validation. `/doctor` reports:

```text
Settings (.claude/settings.json › hooks.UserPromptSubmit.1.hooks):
Expected array, but received undefined
```

Two independent library code paths write the same `UserPromptSubmit` /
`ctx-inject.sh` hook into `.claude/settings.json`, and they disagree on schema:

1. `infrastructure/public_assets.py` (≈ lines 2305-2317) writes the **correct**
   nested Claude Code hook schema:

   ```json
   { "matcher": "", "hooks": [ { "type": "command", "command": ".../ctx-inject.sh" } ] }
   ```

   This becomes entry index 0.

2. `features/workspace/service.py::_configure_hook` (lines 107-129) writes the
   **stale flat/legacy schema** at line 109:

   ```python
   hook_entry = {"type": "command", "command": str(hook_script)}
   ```

   and its "already installed" guard (lines 124-126) only inspects the
   **top-level** `e.get("command")` of each existing entry:

   ```python
   already_installed = any(
       isinstance(e, dict) and e.get("command") == hook_entry["command"] for e in existing
   )
   ```

   The correct nested entry from path 1 has no top-level `command`
   (the command lives at `e["hooks"][i]["command"]`), so the guard **never
   matches**. `_configure_hook` therefore believes the hook is missing and
   appends its flat `hook_entry` as a new array element → entry index 1.

Entry index 1 lacks the required `hooks` array, so
`hooks.UserPromptSubmit.1.hooks` is `undefined` → schema validation fails.

## Impact

- Generated instances ship a `.claude/settings.json` that Claude Code flags as
  invalid on `/doctor`.
- The dedup miss means a malformed duplicate is appended whenever
  `_configure_hook` runs against a settings file whose `UserPromptSubmit` was
  written by `public_assets.py` (nested-only, no top-level `command`). Once the
  flat entry exists, the top-level `command` check matches it, so a single run
  adds **at most one** duplicate; the count grows again only if the flat entry is
  later removed/overwritten (e.g. `public_assets.py` rewrites the nested-only
  form) and `_configure_hook` runs afterward.
- Both entries point at the same `ctx-inject.sh`, so the duplicate is pure noise
  — removing it changes no behavior.

## Steps to reproduce

1. Instantiate / project a dadaia-workspace such that `public_assets.py` writes
   the nested `UserPromptSubmit` entry into `.claude/settings.json`.
2. Run the path that calls `WorkspaceService._configure_hook` (workspace init /
   hook configuration).
3. Inspect `.claude/settings.json` → `hooks.UserPromptSubmit` now has TWO
   entries: index 0 nested (`{matcher, hooks:[...]}`), index 1 flat
   (`{type, command}`).
4. Run Claude Code `/doctor` → reports
   `hooks.UserPromptSubmit.1.hooks: Expected array, but received undefined`.

Observed live 2026-06-07 in this instance at
`/home/[REDACTED]/workspace/dadaia/.claude/settings.json`.

## Environment

- Repo: dadaia-workspace source library
- Files: `dadaia_workspace/features/workspace/service.py` (`_configure_hook`,
  lines 107-129; flat `hook_entry` at 109; dedup at 124-126);
  `dadaia_workspace/infrastructure/public_assets.py` (≈ 2305-2317)
- OS: Linux
- Python: 3.12

## Root cause hypothesis

`_configure_hook` predates / diverges from the nested Claude Code hook schema
used by `public_assets.py`. Two defects compound:

1. **Wrong write schema** — `hook_entry` must be the nested form
   `{"matcher": "", "hooks": [{"type": "command", "command": <path>}]}`, not the
   flat `{"type": "command", "command": <path>}`.
2. **Schema-blind dedup** — the "already installed" check must look inside each
   entry's nested `hooks` array
   (`e.get("hooks", [])` → inner `command`), not at top-level `e.get("command")`.

Proposed fix: make `_configure_hook` emit the nested schema and dedup against the
nested command, OR — preferably — have a single owner of the `UserPromptSubmit`
hook in `settings.json` so the two writers cannot diverge. Whichever path,
existing instances need a one-time de-dup/repair (doctor auto-repair) of the
already-malformed `.claude/settings.json`.

Related: [[repeated-visible-userpromptsubmit-memory-injection]] (separate
concern — hook *output* visibility, not the malformed entry).
