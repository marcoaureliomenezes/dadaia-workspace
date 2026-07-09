---
release: v0.1.69
phase: IMPLEMENTATION
---

# Active release: v0.1.69 — Context Resolution, Session Observability & CLI Surface

**Phase:** IMPLEMENTATION (SPEC/PLAN/TASKS Aprovado; architect REVISE F1a/F1b/F2/F3 folded).

Second of three remediation releases dispositioning the 9 live lifecycle/CLI bugs
reported against `dd-chain-capture v0.2.0` (remote HEAD == main). Release A
(v0.1.68) fixed the engine; Release B fixes the layer an operator touches first:
context resolution, session observability, and the diagnostic CLI surface — so a
bound context is actually visible to every command.

**Picked bugs (4):**
- `codex-thread-id-bind-resolution-breaks-cli` (**CRITICAL**)
- `lifecycle-diagnostic-commands-missing-context-options` (HIGH)
- `lifecycle-preflight-unusable-resolved-runtime-inputs` (MEDIUM)
- `context-bind-success-not-reflected-in-context-show` (MEDIUM)

**Release C (v0.1.70)** — contract/hygiene drift (agent_tier docs, gitignore
intake) — follows. Memory consolidation + remote-bugs archival + post-mortem after C.
