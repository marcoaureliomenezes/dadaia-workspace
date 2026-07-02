---
release: none
phase: none
---

# Active release: none

**v0.1.49** — *Intake Integrity* — is **CLOSED and ARCHIVED** at
`specs/_archive/releases/v0.1.49/` (CLOSURE.md). R1 of the 2026-07-02 operator
sequence: the backlog is now git-tracked repository truth exercised by real BL-*
enforcement (31→30 files), the subject registry's invariant surface is fail-closed
(`specs/memory/**` Markdown only — live set exactly `INV-1..INV-6`), and the
memory-heading allowlist is consumer-extensible (`.heading-allowlist` union) with the
library's own scaffold linting clean. Both picked bugs resolved; consumed entry
removed with durable copy + ledger. Merged as `3743cb06` (PR #87, 38/38 checks green).

No release is active. Next in sequence: **R2 — Kernel hardening** (v0.1.50:
`lease-kernel-identity-hardening` + `context-dead-exit-path` + bug
`bugs-append-bound-session-falls-through-to-cwd-specs`) per
`specs/backlog/candidates.md` §Release sequence.
