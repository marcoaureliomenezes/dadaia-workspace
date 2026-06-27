---
name: pi-headless-command-trailing-dash-breaks-layer2
status: Closed
severity: HIGH
reported: 2026-06-27
surface: infrastructure/pi_runtime.py PiHeadlessAdapter._command
session_id: null
---

> **Closed in release v0.1.31 (2026-06-27).** Solved by the adopted `-p -`→`-p` command fix
> (`c8513fa5`), re-verified by the PI argv unit assertion (A12) and hardened with a real `pi`
> smoke (A13). Evidence: live `tests/integration/pi_live/test_pi_command_smoke.py` PASSED — the
> real `pi` command (pi 0.79.3, gpt-5.5) executes without "Unknown option: -". See
> `specs/_archive/releases/v0.1.31/CLOSURE.md` (Validations + Dispositions).

**Symptom:** Every PI Layer-2 worker invocation fails immediately. `PiHeadlessAdapter._command`
builds `pi --mode json --tools <…> [--model X] -p -`. The installed `pi` rejects the trailing
`-`:
```
Error: Unknown option: -
```
so the worker never runs. A `dadaia lifecycle release define --harness pi` (and any
`pipeline --harness pi`) BLOCKS at the first step with `reason: "Error: Unknown option: -"`,
`runtime: pi_headless` — i.e. the dadaia-workflow engine dispatches to PI correctly, but the
PI command line is malformed, so PI as a Layer-2 worker is effectively **non-functional
headless**.

**Repro:**
```
printf 'Reply with exactly: PONG' | pi --mode json --no-tools -p -   # -> Error: Unknown option: -
printf 'Reply with exactly: PONG' | pi --mode json --no-tools -p     # -> works, streams JSON
```
Or end-to-end:
```
dadaia release new v0.1.31
dadaia lifecycle release define --release-id v0.1.31 --harness pi --json
# -> {"blocked":{"blocked_at_step":"release_scope","reason":"Error: Unknown option: -",...}}
```

**Expected:** The prompt is piped to the worker via **stdin** (`subprocess.run(..., input=self._prompt(request))`,
pi_runtime.py:120). `pi --print/-p` reads the piped stdin when no positional message is given;
the `-` was an incorrect "read from stdin" marker (`pi` has no such option — its CLI is
`pi [options] [@files...] [messages...]`). The fix is to drop the trailing `-`:
`args += ["-p", "-"]` → `args += ["-p"]`.

**Root cause / why it shipped:** `test_pi_runtime.py::test_pi_adapter_builds_controlled_command_and_env`
asserted `argv[-2:] == ["-p", "-"]` against a **fake** runner (`runner=` seam), so the unit
suite froze the wrong command and never invoked the real `pi`. The bug predates this session
(PI headless shipped v0.1.18–v0.1.21); v0.1.30 Wave A faithfully preserved it byte-for-byte
(A4 behavior-preservation). It surfaced only on the first real `--harness pi` workflow run.

**Notes:** No secrets/operator-local paths. Confirmed against the pinned pi build at
`~/.local/share/pi-node/node-v22.22.3-linux-x64/bin/pi`. This directly blocks "PI Layer-2
working properly" — the v0.1.30 PI telemetry/governance work is intact, but no PI worker step
could ever execute until this is fixed.
