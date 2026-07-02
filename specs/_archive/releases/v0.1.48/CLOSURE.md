# CLOSURE — v0.1.48 — Memory Single-Ownership + Truth + English Canon

**Status:** Aprovado
**Branch:** `feature/v0.1.48` · **Base:** `b8c40708` (v0.1.47 merge)
**Origin:** operator directives 2026-07-02 disposing audit
`specs/audits/20260702T015037Z-56b226fb/` (84 findings) + 2 open bugs.

## Summary

Every fact in the memory canon now lives in exactly one owning file, every checkable claim
is true against the code, and the entire specs/memory surface — bodies, frontmatter,
headings, generated catalog/index — is English. The audit's 84 findings are fully
dispositioned (77 fixed across W1–W5, 6 superseded by structural fixes, 1 deferred to a named
backlog entry); both picked bugs are resolved in code with contract tests.

## Shipped (by wave; conventional commits on the feature branch)

- **W0** (`6c3e086e`, `23029d43`) — v0.1.47 archived; audit committed; GRILL (G1–G12) +
  SPEC/PLAN/TASKS `Aprovado` after a real QA REJECT→APPROVE cycle (BLOCKER: the F-06/F-07
  fix mechanism could not reach `specs/memory/AGENTS.md` via install — corrected to a
  tri-copy direct edit + mechanical AC-8; 7 phantom finding IDs restored; TREE-5M
  remediation-text bug registered and picked).
- **W1** (`94e6f0cd`) — 34 truth fixes + 4 extra stale copies the audit missed (bind-epoch
  ×2 in architecture.md, SPEC-DOC-008 falsehood in panel.md); memory-AGENTS tri-copy
  byte-identical (AC-8); AC-1 greps 8/8 = 0.
- **W2** (`78012790`) — 31→25 atom canon. **Deletions (G10):** `ai-harness-codex.md`,
  `ai-harness-claude-code.md`, `ai-context-engineering.md`, `harness-primitives.md`
  (skill-mirror duplicates; unique facts migrated to `harness-codex.md`),
  `agent-sdd-alignment.md` (merged into `agent-orchestration.md`). **Archived:**
  `sdd-hotfix-track.md` → `specs/_archive/memory/`. **Re-homed:** `repos-catalog.md` →
  `product/platform/`. Lease mechanics single-homed in `sdd-gate-v3`; projection facts in
  `public-asset-distribution`; architecture de-enumerated (roster → `[[tech-stack]]`, G7);
  constitution F-11/12/13/19; lifecycle-foundation de-changelogged.
- **W3** (`10a09db5`) — both catalog renderers emit contiguous GFM + identical output shape
  (bug `memory-index-table-broken-gfm`); derived `area` field + area-grouped index;
  `rank` dropped from the ctx-inject digest; TREE-5M remediation text trued (bug
  `specs-doctor-tree5m-remediation-wrong`); lint allowlist gains the English Group-A canon
  (PT legacy kept for consumers, dead strings pruned); new
  `tests/contract/test_memory_catalog_render_contract.py` (8 tests) + lint/digest/doctor
  test updates; archived v0.1.47 CLOSURE completed (SPEC-DOC-006).
- **W4** (`90f0a110`) — full English canon: 16 PT/mixed bodies translated, Group-A headings
  swapped everywhere, frontmatter English, token estimates refreshed, allowlist GROUP_G
  (25 English one-off headings); lint 28 OK / 0 WARN / 0 ERROR; catalog + index regenerated
  (0 diacritics). Justified literals kept: SDD status tokens, the `Histórico`
  forbidden-heading check token, quoted UI/code literals.
- **W5** (`a51e1a8b`) — stray `specs/releases/v0.1.23/` archived with retro-CLOSURE
  (delivered via the v0.1.28/29 PR #68); orphan backlog screenshots and empty `docs/img`
  removed.

## Validations

| Check | Result | Evidence |
|---|---|---|
| pytest (minus CI-only performance dir) | 4377 passed / 17 skipped; sole live-tree failure was the transitional SPEC-DOC-024, cleared by this CLOSURE flip | W3 full-gate run + W6 pre-push preflight |
| ruff format --check + ruff check | clean (750 files) | W3 gate |
| mypy --strict | 0 issues (298 files) | W3 gate |
| lint-memory-atoms | 28 OK / 0 WARN / 0 ERROR | W4 integration run |
| specs doctor | 0 errors after CLOSURE flip | W6 run |
| backlog doctor / workflows doctor / public doctor | clean / ok / exit 0 | W5 runs |
| AC-1..AC-8 (SPEC §6) | all mechanical checks pass (greps 0, catalog 25, area on every entry, GFM contiguous, tri-copy identical) | per-wave verification |

## Drifts / residuals (tracked, not dropped)

- F-76 deferred: `agent_tier` wire-or-remove → `specs/backlog/hygiene-and-dead-code-cleanup.md`
  (also gains the dead `TelemetryService.list_workflows()` call W2 found).
- PT legacy heading allowlist entries retained deliberately (consumer-workspace compat, G2).
- `specs/_archive/v0.1.47/consumed-backlog/` sidecar entered version control in W3's sweep
  commit — kept (archive-class durable data; supersedes the untracked-by-design note).

## Memory updates

All 28 memory files re-trued/translated carry `last_updated: '2026-07-02'`,
`release_origin: v0.1.48`; catalog + index regenerated last (25 features, 7 areas).
CLOSURE-phase edits: ACTIVE flip + this file + terminal bug events + audit archive with
DISPOSITION.md. Release-dir archive move follows the merge (closure commit pattern).
