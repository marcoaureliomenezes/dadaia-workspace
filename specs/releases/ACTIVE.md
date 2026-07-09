---
release: none
phase: none
---

# Active release: none

**v0.1.68 — Lifecycle Evidence/Handoff Engine Correctness** shipped and closed
2026-07-09: merged `b1e469f8` (PR #130, all CI green incl. post-merge main);
closure on `chore/v0.1.68-closure`. Fixed 3 HIGH lifecycle-engine bugs at root
cause (FR1 removed the run-unscopable block-evidence disk-glob; FR2 terminal
review declares no phantom consumer; FR3 derives implement write-scope from
TASKS.md) + added the missing full-pipeline E2E. QA PASS 4996/0 with
mutation-sanity; ledger 3 resolved. Specs archived to `specs/_archive/releases/v0.1.68/`.

**Remediation arc (3 releases dispositioning 9 live dd-chain-capture bugs):**
- ✅ **A — v0.1.68** lifecycle evidence/handoff engine (3 HIGH) — CLOSED
- ⏭️ **B — v0.1.69** context resolution, session observability & CLI surface —
  `codex-thread-id-bind-resolution-breaks-cli` (CRITICAL),
  `lifecycle-diagnostic-commands-missing-context-options` (HIGH),
  `lifecycle-preflight-unusable-resolved-runtime-inputs` (MEDIUM),
  `context-bind-success-not-reflected-in-context-show` (MEDIUM)
- ⏭️ **C — v0.1.70** contract/hygiene drift —
  `specs-doctor-rejects-current-memory-agent-tier-frontmatter` (HIGH),
  `remote-bugs-gitignore-blocks-new-intake` (HIGH)

Ledger: 6 open. Memory consolidation + remote-bugs archival + full post-mortem
happen once, after Release C.
