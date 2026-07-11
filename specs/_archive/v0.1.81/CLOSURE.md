# CLOSURE — Release v0.1.81 — Deprecation strips & doctor cleanup

**Shipped:** PR #159, squash-merged to main as `11cfd37c` (2026-07-11). All PR checks
green; post-merge main CI green.

## Waiver record

The entry's ship-on/after-2026-08-01 constraint was **explicitly waived by the
operator on 2026-07-11**. Accepted consequence (SPEC-documented, security-verified):
stale consumers degrade with the two standard warnings (unknown-field drop + band-3
default) until `dadaia public install` — never a crash.

## Delivered

- FR1 (breaking): the v0.1.64 `tier:` tolerate window closed — fallback read stripped,
  allowlist key dropped, `MissingTierError` alias + re-export deleted; AC-6 test
  flipped to the unknown-key truth. Registry `Tier` + pinned model/effort contract
  untouched (test-verified).
- FR2: SPEC-DOC-039 WARNING invariant — artifact-empty `_archive/releases/<id>/` dirs
  flagged as residue (v0.1.41 precedent); SPEC-DOC-027 allowlist honored, segmented
  layouts tolerated, wip-abandoned relocation suggested. Own tree: zero fires. TDD
  caught a generator-truthiness bug in the first cut before it shipped.

## Dispositions

- Backlog `deprecation-strips-and-doctor-cleanup`: **delivered**, archived (waiver
  recorded in its frontmatter).

**State after closure: the backlog is EMPTY — every entry of the 2026-07-10
consolidation is delivered. 0 open bugs, 0 open audits.**

## Validations

- Full suite 2,891 passed / 10 skipped / 0 failed; mypy --strict clean; ruff clean;
  specs doctor 0 errors; public doctor no drift; doctor goldens unchanged.
- QA APPROVED (independent re-execution of every check + main-worktree warning-count
  comparison); security APPROVED (deleted symbols carried no security logic; rglob
  symlink/cycle behavior empirically verified — no CWE-22/CWE-400 exposure).
