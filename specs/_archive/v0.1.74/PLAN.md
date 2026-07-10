# PLAN: Release v0.1.74

**Status:** Aprovado
**Release ID:** v0.1.74
**Owner:** product-engineer

One insertion point: `hygiene._protected_paths()` walks each safe zone for
`_CANONICAL_ZONE_DOC_NAMES` and protects them as `CANONICAL_ZONE_DOC` (new enum kind).
Cleanup skip, preflight arithmetic, and the D5 retention sweep (protected_refs) inherit.
RED-first unit test (reporter's exact expired-AGENTS scenario + stale-sibling control +
apply-survival); mutation-sanity; full suite; remote replay as the acceptance gate.
