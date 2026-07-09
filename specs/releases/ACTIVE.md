---
release: none
phase: none
---

# Active release: none

**REMEDIATION ARC COMPLETE (v0.1.68 -> v0.1.70).** All 9 live dd-chain-capture bugs
(reported against remote HEAD == main 54e9be0e) fixed at root cause, RED-first, no
workarounds, validated with mutation-sanity + full-pipeline/bound-context E2Es, shipped
and closed:
- v0.1.68 (PR #130/#131) — lifecycle evidence/handoff engine (3 HIGH)
- v0.1.69 (PR #132/#133) — context resolution & CLI surface (1 CRITICAL + 3)
- v0.1.70 (PR #134) — contract/hygiene drift (2 HIGH)

Remote-bugs intake archived (redacted) to specs/backlog/remote-bugs/_archive/. Memory
consolidated (quality-assurance.md: workflow-boundary validation law + 3 more).
Post-mortem in specs/_archive/releases/v0.1.70/CLOSURE.md. Ledger: 1 open
(stray-dadaia-tmp-inside-repo, a tracked AI-surface side-bug found during the arc).
Backlog follow-ups: preflight-block-reasons-missing-operator-command,
tasks-write-scope-traversal-hardening, implement-review-write-scope-from-tasks-parity.
