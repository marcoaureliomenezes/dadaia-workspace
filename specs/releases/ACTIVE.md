---
release: none
phase: none
---

# Active release: none

**v0.1.69 — Context Resolution, Session Observability & CLI Surface** shipped and
closed 2026-07-09: merged `3388afde` (PR #132, all CI green incl. post-merge main);
closure on `chore/v0.1.69-closure`. Fixed 4 CLI/context bugs (1 CRITICAL): FR1
recognizes `CODEX_THREAD_ID` (+ lock.py identity + ENTRY_SIGNAL safety envelope), FR2
`--context` on preflight/specs-doctor, FR3 built the preflight-input probe assembly &
retired the inert stub, FR4 `context show` reads the incumbent pointer. QA PASS 5021/0
with mutation-sanity 4/4. Specs archived to `specs/_archive/releases/v0.1.69/`.

**Remediation arc (3 releases dispositioning 9 live dd-chain-capture bugs):**
- ✅ **A — v0.1.68** lifecycle evidence/handoff engine (3 HIGH) — CLOSED
- ✅ **B — v0.1.69** context resolution, session observability & CLI surface (1 CRIT + 3) — CLOSED
- ⏭️ **C — v0.1.70** contract/hygiene drift —
  `specs-doctor-rejects-current-memory-agent-tier-frontmatter` (HIGH),
  `remote-bugs-gitignore-blocks-new-intake` (HIGH)

Ledger: 3 open (2 for Release C + `stray-dadaia-tmp-inside-repo` MEDIUM side-bug,
tracked). Memory consolidation + remote-bugs archival + full post-mortem after Release C.
