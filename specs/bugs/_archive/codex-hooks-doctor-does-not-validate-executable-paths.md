---
name: codex-hooks-doctor-does-not-validate-executable-paths
status: Closed
severity: MEDIUM
reported: 2026-06-13
surface: dadaia public doctor D-CX-9 / .codex/hooks.json generated command paths
session_id: sess_0bac2bc0
---

**Symptom:** `dadaia public doctor` reports `[ok] codex:hooks.json` when the generated
Codex hook commands merely contain the expected module names
(`dadaia_workspace.hooks.pre_gate`, `sdd_post_gate`, `ctx_inject`). It does not validate
that the command's interpreter path exists on the current machine or that
`python -m dadaia_workspace.hooks.<module>` can import and start. In a copied or
partially restored workspace, `.codex/hooks.json` can still point at an absolute Python
path from another machine, causing every PreToolUse/PostToolUse command hook to fail
while doctor stays green.

**Repro:**
1. Generate or copy a `.codex/hooks.json` whose commands point at a nonexistent Python,
   for example `/old/machine/workspace/.dadaia/.venv/bin/python -m
   dadaia_workspace.hooks.pre_gate`.
2. Run `dadaia public doctor`.
3. Observe `[ok] codex:hooks.json` as long as the JSON still mentions the expected
   module strings.
4. Start Codex in the trusted project and trigger a write/read tool: command hooks fail
   at process launch because the interpreter path is stale.

**Expected:** D-CX-9 should validate the executable side of the hook contract:
the configured interpreter exists (or is intentionally portable), the hook command is
portable for the host OS, and each module can be invoked with minimal stdin without a
process-launch/import error. If a workspace was moved, doctor should report a clear
repair action such as `dadaia public install --target codex` or `--target all`.

**Notes:** Found while diagnosing operator report that all Codex PreToolUse/PostToolUse
hooks fail on another machine. Local projection contains absolute host paths by design
after install; import rewrites known JSON paths, but manual copy/partial restore or a
missing `.dadaia/.venv` leaves a failure mode that the doctor currently misses.

**Resolution (2026-06-14):** D-CX-9 was rewritten to validate the executable side of the
hook contract. It now (1) asserts each `.codex/hooks.json` command is one of the four
`.dadaia/hooks/*` wrapper paths and flags any stale shell-command string with
`must use .dadaia/hooks wrapper`, (2) verifies each wrapper exists and is executable, and
(3) actually launches each wrapper with a minimal probe payload and flags a non-zero exit.
Because the wrappers resolve the venv Python relative to their own location, the copied/
moved-workspace stale-path case is both prevented (wrappers self-locate) and detected
(launch probe fails if `.dadaia/.venv` is missing). Fixed together with
[[codex-hook-command-strings-fail-code-127-on-vps]] on branch
`fix/codex-hook-direct-exec-wrapper`; new tests `test_dcx9_non_executable_wrapper_detected`
and `test_dcx9_shell_command_string_detected` cover the added checks; `dadaia public doctor`
exit 0.
