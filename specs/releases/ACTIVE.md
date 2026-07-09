---
release: v0.1.71
phase: IMPLEMENTATION
---

# Active release: v0.1.71 — Remediation: real-consumer TASKS grammar + diagnostic surface + evidence-doctor

Remediation of 4 bugs re-verified STILL OPEN on the operator's remote against installed
source `574a84bd` (== main). The v0.1.68–70 arc marked these resolved but validated only
against internal fixtures / fake harnesses — never against the real `dd-chain-capture`
consumer artifacts. This release fixes each at root cause and its acceptance gate is
**validation on the operator's remote against the real consumer**, not the local suite.

- FR1 (HIGH) `pipeline-write-scope-parser-wrong-grammar` — parser handles the real
  consumer TASKS.md grammar (bold `**T-x —**` headings, fenced `[-] T-x.y` marker blocks,
  plain `- Write set:` key, per-path parentheticals) as well as the internal grammar.
- FR2 (HIGH) `lifecycle-status-handoffs-doctor-missing-context` — `lifecycle status` and
  `lifecycle handoffs doctor` accept `--context`/`--release-id` as REAL run filters.
- FR3 (MEDIUM) `context-show-noarg-ignores-bound-session` — no-arg `context show` resolves
  to the context with a live bound session before first-ALIVE.
- FR4 (HIGH) `handoffs-doctor-blocks-terminal-promote-to-evidence` — doctor exempts
  `promote_to_evidence` payloads from `unconsumed_required`; heals existing runs, no migration.
