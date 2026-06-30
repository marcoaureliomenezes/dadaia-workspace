---
name: context-release-ignores-persisted-bind-and-requires-dadaia_session_id-env
status: Closed
severity: "MEDIUM"
reported: 2026-06-29
surface: lifecycle bug report workflow
session_id: null
---

# context release ignores persisted bind and requires DADAIA_SESSION_ID env

**Symptom:** context release ignores persisted bind and requires DADAIA_SESSION_ID env

## Details

After '.dadaia/.venv/bin/dadaia context bind dadaia-workspace --mode implementation --release v0.1.41' returned session id sess_bd01c195, '.dadaia/.venv/bin/dadaia context release' failed with 'No active session. Pass --session <id> or set DADAIA_SESSION_ID'. Re-running with '--session sess_bd01c195' succeeded. This is the same persisted-bind contract class as the specs-doctor resolution bugs, but on context release cleanup.

## Repro

1. Run .dadaia/.venv/bin/dadaia context bind dadaia-workspace --mode implementation --release v0.1.41. 2. Run .dadaia/.venv/bin/dadaia context release without exporting DADAIA_SESSION_ID. 3. Observe failure. 4. Run with --session <printed id> and observe success.

## Expected

context release should resolve the persisted bound session created by context bind, or context bind should expose a cleanup-safe release command without requiring shell eval/env export.

## Actual

context release reports no active session unless --session or DADAIA_SESSION_ID is provided, even immediately after successful persisted bind.
