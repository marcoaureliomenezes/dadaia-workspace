# Codex thread session is invisible to dadaia CLI context resolution

- Bug ID: `codex-thread-id-bind-resolution-breaks-cli`
- Severity: CRITICAL
- Surface: Codex entry sessions running `dadaia` CLI commands
- Component: `dadaia_workspace.core.session_env`, `dadaia context bind`, CLI specs resolution
- Reported: 2026-07-08T22Z
- Event stream mirror: `repos/dadaia-workspace/specs/bugs/20260708T22Z-00.jsonl`

## Symptom

In a live Codex entry session, `dadaia context bind dadaia-workspace` succeeds, but
resolver-driven CLI commands still cannot find the bound context:

```text
.dadaia/.venv/bin/dadaia bugs status
Could not resolve specs_dir. Pass --specs-dir or run inside a context/repo.
```

This affects any command that depends on implicit active-context/specs resolution,
including bug, specs, memory, and lifecycle commands that rely on the current bound
session.

## Reproduction

From a trusted Codex workspace session:

```bash
.dadaia/.venv/bin/dadaia context bind dadaia-workspace
.dadaia/.venv/bin/dadaia bugs status
```

Observed diagnostics in the same process environment:

```text
CODEX_THREAD_ID=019f3f5a-ce5c-76d1-86b8-79f3473ac1dc
CODEX_SESSION_ID=None
harness_session_id=None
entry_harness=None
```

Inside the Codex tool subprocess, the parent process resolves to PID `1`, so the
existing ancestry fallback cannot discover the bound session record.

## Root Cause

`HARNESS_SESSION_ID_ENV_VARS` currently recognizes `CLAUDE_CODE_SESSION_ID` and
`CODEX_SESSION_ID`, but current Codex sessions expose `CODEX_THREAD_ID` instead.
Because `harness_session_id()` returns `None`, `context bind` does not persist a
session record keyed by the live Codex thread id. Because `entry_harness()` also checks
only `CODEX_SESSION_ID`, Codex entry-harness auto detection is invisible in the same
runtime.

The fallback path in CLI specs resolution builds ancestry from `os.getppid()`, but the
Codex sandbox process tree collapses to PID `1`, leaving no useful harness ancestry to
walk.

## Expected

After a successful `dadaia context bind dadaia-workspace`, Codex users should be able
to run context-aware CLI commands without passing `--specs-dir` manually.

The same Codex session signal should also make `entry_harness()` resolve to `codex`
where automatic harness selection depends on the entry runtime.

## Workaround

Use explicit specs resolution:

```bash
.dadaia/.venv/bin/dadaia bugs status --specs-dir repos/dadaia-workspace/specs
```

This is not sufficient for normal Codex operation because it bypasses the contract that
`context bind` establishes active context for the session.

## Fix Direction

Treat `CODEX_THREAD_ID` as a first-class Codex session id:

- include it in `HARNESS_SESSION_ID_ENV_VARS`
- make `entry_harness()` treat it as a Codex entry signal
- ensure `context bind` writes or refreshes the thread-keyed session record
- add regression coverage for current Codex environments where `CODEX_SESSION_ID` is
  absent and `CODEX_THREAD_ID` is present
