---
name: lifecycle-codex-exec-ask-for-approval-invalid
status: Closed
severity: HIGH
reported: 2026-06-27
surface: dadaia lifecycle release define (codex harness / codex_exec runtime)
session_id: sess_2c223769
---

**Symptom:** Running `dadaia lifecycle release define --context dd-chain-capture --release-id v0.1.2 --harness codex` fails in the `release_scope` step. The workflow blocks with:

```
error: unexpected argument '--ask-for-approval' found

  tip: to pass '--ask-for-approval' as a value, use '-- --ask-for-approval'

Usage: codex exec [OPTIONS] [PROMPT]
       codex exec [OPTIONS] <COMMAND> [ARGS]
```

**Repro:**
1. Bind context `dd-chain-capture`.
2. Run: `dadaia lifecycle release define --context dd-chain-capture --release-id v0.1.2 --harness codex`
3. Observe `BLOCKED release-define run=release-define phase=blocked release_scope:BLOCKED` and the error above in `.dadaia/states/lifecycle/release-define.json`.

**Expected:** The lifecycle workflow should invoke `codex exec` with flags that the installed `codex` CLI accepts, or surface a clear configuration hint if an unsupported/older Codex CLI is detected. The workflow should advance through `release_scope` and the subsequent typed gates.

**Notes:**
- Installed Codex CLI version: `codex-cli 0.142.3`.
- `codex exec --help` shows no `--ask-for-approval` flag; approval behavior is configured via `config.toml` or `-c` overrides.
- The blocked run state is stored at `.dadaia/states/lifecycle/release-define.json` (run id `release-define`).
- This blocks any Codex-harnessed lifecycle workflow; other harnesses (`fake`, `pi`) may be unaffected.

## Resolution

Fixed in `v0.1.35`.

`CodexExecAdapter._command()` no longer emits the stale `--ask-for-approval` flag. The
adapter leaves approval behavior to Codex config / command policy and controls only
sandbox, cwd, model/effort, git trust bypass, and output capture.

Evidence:

- `dadaia_workspace/infrastructure/codex_runtime.py#CodexExecAdapter._command`
- `specs/releases/v0.1.35/alpha-1/TASKS.md` T-35-04 Codex smoke:
  `v0135-codex-scope-smoke` completed `release_scope` on `codex_exec`.
