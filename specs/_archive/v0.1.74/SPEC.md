# SPEC: Release v0.1.74 — Canonical zone docs are never hygiene waste

**Status:** Aprovado
**Release ID:** v0.1.74
**Owner:** product-engineer

## FR1 (HIGH, `public-install-restores-expired-zone-agents-reblocks-preflight`)
Zone doc files (`AGENTS.md`, `README.md`, `.gitkeep`) anywhere in a hygiene safe zone are
canonical (the scoped-rules / zone-documentation mechanism, lib-projected with historical
mtimes) — protected as `canonical_zone_doc`, never reclaimable:
- cleanup (`clean --apply`) never deletes them;
- the preflight hygiene arithmetic (v0.1.72 FR3: unprotected = candidates − protected)
  passes on a freshly-installed projection;
- the retention sweep inherits via `protected_refs()`;
- a genuinely stale sibling in the same zone still counts unprotected (gate keeps teeth).

**Acceptance:** remote replay — `public install --target all --force` then
`hygiene status` shows 0 unprotected candidates and preflight's hygiene gate passes;
`clean --apply` leaves the docs in place (no doctor drift loop).

## Non-goals
mtime handling in `public install` (would re-expire every TTL window — not the cause).
