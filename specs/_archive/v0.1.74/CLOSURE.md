# CLOSURE — Release v0.1.74 — Canonical zone docs are never hygiene waste

**Release ID:** v0.1.74
**Status:** Aprovado

## Summary

| Bug | Fix | Disposition |
|---|---|---|
| `public-install-restores-expired-zone-agents-reblocks-preflight` (HIGH) | FR1 — zone-root doc files (`AGENTS.md`/`README.md`/`.gitkeep`) protected as `canonical_zone_doc` in ONE insertion point (`_protected_paths`); cleanup, the v0.1.72 FR3 preflight arithmetic, and the D5 retention sweep inherit | resolved |

## Validations

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | PASS — 5075 passed, 19 skipped in 885.77s | `pytest -p no:cacheprovider` |
| Mutation-sanity | PASS — hygiene.py revert → targeted test RED | local |
| Remote replay (reporter's exact commands, live workspace) | PASS — `public install --force` → docs protected (25→27), `clean --apply` leaves both AGENTS.md in place, `public doctor` exit 0 (loop broken), post-clean **unprotected 0 → hygiene gate PASS** | replay transcript |
| ruff / mypy --strict | PASS | pre-push + CI |
| Security | APPROVED keyed to pushed sha | handoff |
| CI (full matrix) | GREEN — PR #143 merged `7b08beef` | GitHub Actions |

## Drifts
None. Classification-only change (mtime handling deliberately untouched — non-goal).

## Memory updates
None — instance of the v0.1.72 gate-coherence law (a gate must not demand what its
tooling refuses); law already durable.

## Next
Ledger after disposition: 0 open.
