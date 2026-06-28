---
name: context-bind-rewrites-incumbent-pointer-away-from-live-holder
status: Closed
severity: HIGH
reported: 2026-06-28
resolved_in: v0.1.34
surface: dadaia context bind / specs doctor SPEC-DOC-029
session_id: null
---

**Resolution (v0.1.34):** `dadaia context bind` now preserves live lease-holder
identity. When a live holder exists, bind does not move `.dadaia/sessions/runtime/<ctx>.ptr`
to the CLI's throwaway session id. For a caller-owned lease-taking rebind, it updates the
holder session record plus lock release/mode metadata under the lease CAS and keeps the
incumbent pointer on the holder. For a foreign live holder, it writes only the CLI session
record and bind-epoch marker.

**Symptom:** Running `dadaia lifecycle review security --harness codex --json` rejected
the release and reported that `dadaia specs doctor --specs-dir <repo>/specs` had one
current error: `SPEC-DOC-029` session identity incoherence. The live lock holder still
named the old harness session/release while `dadaia context bind ... --release v0.1.34`
had moved the incumbent pointer and session record to a fresh CLI-created `sess_*` id.

**Repro:**
1. Hold a live implementation lease for a context from a long-lived harness session.
2. Run `dadaia context bind <context> --mode implementation --release <new-release>` from
   the same operator flow.
3. Run `dadaia specs doctor --specs-dir <context-specs>`.
4. Observe `SPEC-DOC-029` because lock-holder, incumbent pointer, and session record name
   different session ids.

**Expected:** Binding a context while a live holder exists must not create a
doctor-visible identity split. The live lock holder is the coherent runtime identity until
the lease is released or reclaimed.

**Root Cause:** `context bind` always wrote the incumbent pointer to the newly minted CLI
session id. That id is intentionally not the harness-native lock holder in the default
bind flow. The code relied on a later MUTATING write to self-correct the pointer via
`lease.acquire`, but `specs doctor` runs before that later write and correctly observed
the persistent split.

**Evidence:** Regression coverage:
`tests/contract/cli/test_cli_context.py::test_context_bind_implementation_rebinds_same_harness_live_holder_coherently`
and
`tests/contract/cli/test_cli_context.py::test_context_bind_read_does_not_move_incumbent_from_live_holder`.
After applying the fix and rebinding the live context, `dadaia specs doctor --specs-dir
<context-specs>` reports 0 errors.

