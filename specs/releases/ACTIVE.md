---
release: v0.1.74
phase: IMPLEMENTATION
---

# Active release: v0.1.74 — Canonical zone docs are never hygiene waste

Single-bug remediation (HIGH, reported against `45da12e5` from the operator's remote):
`public install` restores the projected zone-doc `AGENTS.md` files with historical
mtimes → 2 UNPROTECTED expired candidates → preflight re-blocked → `hygiene clean
--apply` deletes them → `public doctor` drifts → install restores → loop.

Root cause: the hygiene zone scan has no concept of canonical zone docs / lib
projections — mtime freshening would only re-expire in 24h; classification is the fix.
FR1: zone-root doc files (`AGENTS.md`, `README.md`, `.gitkeep` — the documented
scoped-rules mechanism) get `HygieneProtectionKind.CANONICAL_ZONE_DOC` in ONE insertion
point (`_protected_paths`), inherited by cleanup, the FR3 preflight arithmetic, and the
retention sweep. Acceptance: remote replay of the reporter's exact commands.
