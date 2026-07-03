---
name: codex-hook-command-strings-fail-code-127-on-vps
status: Closed
severity: HIGH
reported: 2026-06-13
surface: .codex/hooks.json command execution on Codex VPS/VS Code surface
session_id: sess_0bac2bc0
---

**Symptom:** On a VPS running `codex-cli 0.139.0`, every dadaia Codex hook reports
`hook exited with code 127` in the Codex UI:

- `UserPromptSubmit hook (failed) error: hook exited with code 127`
- `PreToolUse hook (failed) error: hook exited with code 127`
- `PostToolUse hook (failed) error: hook exited with code 127`

The project `.codex/hooks.json` contains the expected generated commands pointing at
the VPS-local workspace Python, for example
`/home/[REDACTED]/workspace/.dadaia/.venv/bin/python -m dadaia_workspace.hooks.pre_gate`.
The interpreter exists and direct imports work. Running the exact commands through
`/bin/sh -c` exits `0`, including the env-prefixed `ctx_inject` command.

**Repro evidence supplied by operator (VPS):**

```text
pwd -> /home/[REDACTED]/workspace
.codex/hooks.json command -> /home/[REDACTED]/workspace/.dadaia/.venv/bin/python -m ...
ls -l .dadaia/.venv/bin/python -> exists, executable
.dadaia/.venv/bin/python --version -> Python 3.12.3
import dadaia_workspace -> .dadaia/.venv/lib/python3.12/site-packages/dadaia_workspace/__init__.py
/bin/sh -c '<hook command>' </dev/null -> post=0, pre=0, prompt=0
codex --version -> codex-cli 0.139.0
codex doctor --summary --ascii -> 0 fail
~/.codex/hooks.json -> absent/empty
~/.codex/config.toml hook refs -> absent/empty
```

**Expected:** If Codex loads project hooks, the generated command strings should run
the same way they run under `/bin/sh -c`, or dadaia should generate a more robust hook
shape for Codex surfaces that launch commands without shell splitting. Hook failures
must not be hidden by `dadaia public doctor`.

**Likely root cause:** The VPS Codex surface is not executing hook `command` strings
through shell parsing compatible with the documented CLI behavior, so a command string
containing spaces (`<python> -m <module>`) is treated as an executable path and fails
with `ENOENT`/exit 127. A robust projection may need generated wrapper executables
with no spaces in the hook command, or an explicit Codex-surface compatibility test
that covers the operator's launch path.

**Notes:** This is distinct from stale absolute-path failures: the configured path
exists and the exact commands succeed outside Codex. It is also distinct from user-level
hook collisions: no user hook sources were found in the operator's `~/.codex` scan.

**Resolution (2026-06-14):** Confirmed root cause — the Codex surface direct-execs the
hook `command` string instead of shell-parsing it, so any command containing spaces or
an env-prefix (`DADAIA_HOOK_OUTPUT=… <python> -m <module>`) is treated as a single
executable path and fails with exit 127. Fixed by generating direct-exec-safe executable
wrappers under `.dadaia/hooks/` (`codex-pre-gate`, `codex-post-gate`, `codex-ctx-inject`,
`codex-ctx-inject-session-start`); `.codex/hooks.json` commands are now bare wrapper paths
with no spaces and no env-prefix. Each wrapper resolves the workspace venv Python relative
to its own location (`$SCRIPT_DIR/../..`), exports any required env, and `exec`s
`python -m <module> "$@"`, also eliminating the stale-absolute-path failure mode on
moved/copied workspaces. `runtime_config.codex_hook_wrapper_contents()` is the generator;
`public install` writes + chmods the wrappers; `doctor` D-CX-9 now launches each wrapper
to verify it actually starts. Landed on branch `fix/codex-hook-direct-exec-wrapper`;
231/231 codex+public_assets tests green; `dadaia public doctor` exit 0 with `[ok]` on all
four wrappers and `codex:hooks.json`.
