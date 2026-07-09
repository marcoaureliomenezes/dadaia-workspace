---
release: none
phase: none
---

# Active release: none

**v0.1.73 SHIPPED + CLOSED (PR #141 `9b4eb78d`).** Governance hygiene: the bug ledger is
ONE append-only `specs/bugs/bugs.jsonl` (+ one `_archive/archive.jsonl`) — self-applied
via the real `specs upgrade` v2→4; backlog entries carry `YYYYMMDD-` first-commit
prefixes with `candidates.md` as the index; `resolved` events REQUIRE
`--resolution-evidence` (the blocking resolution law — its redaction gap was caught by
the security gate's REJECT before shipping and fixed RED-first); agent-tier ReDoS,
out-of-worktree upgrade backups, REPO-DADAIA-1 doctor invariant.

**Bug ledger: 0 open.** Backlog: 8 timestamped entries; top pick for the next release:
`20260709-central-bind-resolution-seam` (HIGH — recurrence family F2 class-level fix).
