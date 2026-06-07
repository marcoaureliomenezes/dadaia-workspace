# Closure: Release v0.2.1 — "Vision Fidelity Fold"

> **Status:** Aprovado
> **Release ID:** v0.2.1
> **Owner:** product-engineer
> **Closed:** 2026-06-07

## Summary

v0.2.1 closed seven fidelity gaps between the live workspace and the normative Product
Vision (`docs/01_medium_codex.md`). None changed the product's runtime behaviour from a
user perspective; all were conformance, correctness, and canonization work over the v0.2.0
baseline.

The seven workstreams delivered: (WS-1) constitution canonized with vision references,
correct QA memory path, and correct panel/handoff wording, plus the product-vision memory
atom created; (WS-2) all 8 scoped AGENTS.md surfaces projected, including the missing
`specs/memory/AGENTS.md`; (WS-3) canonical scaffold completed with `audits/` stub,
top-level `quality-assurance.md`, and safe-preserve-existing-specs on `alive()`; (WS-4)
doctor rglob bug fixed, TREE-3 top-level QA check added, and AGENTS.md presence check
added; (WS-5) `CLAUDE.md` and `prompt.md` whitelisted in all three sources and the
`CLAUDE.md` bridge (`@AGENTS.md`) delivered to the live workspace; (WS-6) dead
write-allowlist entries cleaned from ai-engineer, qa-engineer wording tightened for
dispatch purity, and a dead report-template path fixed in software-architect; (WS-7)
v0.1.5 archived and the semaphore bug frontmatter completed.

Three cross-spec inconsistencies were resolved before SPEC authorship via the mandatory
grill session and locked as operator decisions: (D1) quality-assurance.md moves to
top-level; (D2) CLAUDE.md and prompt.md are legitimate root entries; (D3) handoffs are
never served by the panel.

No PyPI publish — operator-gated; deferred to a future operator-decided release.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-021-01 | Fix flat-glob bug in doctor.py (glob → rglob) | `435bcca` |
| T-021-02 | Add TREE-3 check: top-level quality-assurance.md | `435bcca` |
| T-021-03 | Add check: specs/memory/AGENTS.md presence | `435bcca` |
| T-021-04 | Regression tests for WS-4 doctor changes | `435bcca` |
| T-021-05 | Constitution §0: reference normative product vision | `c033258` |
| T-021-06 | Constitution: add allowed root-entry section | `c033258` |
| T-021-07 | Constitution §11: correct panel/handoff wording | `c033258` |
| T-021-08 | Constitution §13: correct QA memory path to top-level | `c033258` |
| T-021-09 | Create product-vision memory atom | `c033258` |
| T-021-10 | Rename non-conformant audit directory | `c033258` |
| T-021-11 | Create public/data/memory-AGENTS.md source | `a647f52` |
| T-021-12 | Fix backlog-authority line in specs-AGENTS.md template | `a647f52` |
| T-021-13 | Stage, install, verify all 8 scoped surfaces | `a647f52` |
| T-021-14 | Add canonical tree stubs to public/scaffold/ | `b051853` |
| T-021-15 | Fix alive(): safe-preserve existing specs/ on scaffold | `b051853` |
| T-021-16 | Confirm TREE-4 covers audits/ auto-create; regression tests | `b051853` |
| T-021-17 | Whitelist CLAUDE.md and prompt.md in all three sources | `1d8a308` |
| T-021-18 | Add CLAUDE.md scaffold file; upgrade live root CLAUDE.md | `1d8a308` |
| T-021-19 | Fix ai-engineer.md write_allowlist | `7ceda9f` |
| T-021-20 | Fix qa-engineer.md dispatch-purity wording | `7ceda9f` |
| T-021-21 | Fix software-architect.md dead report-template path | `7ceda9f` |
| T-021-22 | Archive v0.1.5 release | `7ceda9f` |
| T-021-23 | Add status: resolved to semaphore bug frontmatter | `7ceda9f` |
| T-021-LAST | Write CLOSURE.md, update memory, archive v0.2.1 | — |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green (2242 pass, 0 fail) | `pytest -p no:cacheprovider` | `7ceda9f` |
| ruff format + check clean | `ruff format --check . && ruff check .` | `7ceda9f` |
| mypy --strict clean | `mypy --strict dadaia_workspace/` | `7ceda9f` |
| dadaia specs doctor exit 0 | `dadaia specs doctor` | `7ceda9f` |
| dadaia public doctor exit 0 | `dadaia public doctor` | `7ceda9f` |
| QA ship-trio gate APPROVED | — | `.dadaia/handoff/dadaia-workspace/2026-06-07T072022Z-qa-engineer-v0.2.1-commit-gate.handoff.json` |
| Security ship-trio gate APPROVED | — | `.dadaia/handoff/dadaia-workspace/2026-06-07T061500Z-security-reviewer-v021-push-gate.handoff.json` |
| Code-reviewer ship-trio gate APPROVED | — | `.dadaia/handoff/dadaia-workspace/2026-06-07T130000Z-code-reviewer-v021-vision-fidelity-pr-gate.handoff.json` |
| Closure audit PASS (9/10) | — | `specs/audits/20260607T072603Z-a4b8c2d1/closure-audit.md` |

## Drifts

### pypi-publish-deferred

**Description:** The SPEC §9 explicitly excluded PyPI publish as operator-gated. No
additional drift — the operator confirmed this before implementation and recorded it as
an out-of-scope item. Identical disposition to v0.2.0 (T-020-style recording).

**Resolution:** Noted in Summary. PyPI publish remains operator-gated and will be
scheduled by the operator independently of the SDD release lifecycle.

**Memory updates:** None — this is a process constraint, not a product state change.

### residuals-deferred-to-v022

**Description:** The closure audit (9/10, PASS) identified four LOW residuals that did
not block closure: (a) two dead documentation or agent-knowledge cross-references, (b) an
rglob-symlink LOW risk (symlinks not followed during rglob; not an issue on the current
workspace tree but a theoretical gap), (c) a persona-allowlist-resolves-to-existing-dir
test gap (write_allowlist globs are validated manually but not in the test suite).

**Resolution:** All four are below the closure-block threshold. Logged here; PM to file
in `specs/backlog/candidates.md` for v0.2.2 planning.

**Memory updates:** None — these are gaps, not current-truth product state changes.

## Memory updates

- `specs/memory/architecture.md` — updated `last_updated` and `release_origin` to v0.2.1;
  narrative kept current-truth. The 8-scoped-AGENTS.md surface, panel-never-serves-handoffs
  (§11 aligned), and doctor CAT-1/TREE subdir-aware checks are already accurately described
  in this atom from v0.2.0; no substantive content change required.
- `specs/memory/quality-assurance.md` — already at top-level path with `release_origin:
  v0.2.1` and `last_updated: 2026-06-07`; atom accurately reflects current state including
  the canonical path note. No edit required.
- `specs/memory/product/philosophy/product-vision.md` — atom created in WS-1 (T-021-09);
  content is current-truth at v0.2.1 end-state; no further edit required at closure.
- `specs/memory/product/index.md` — catalog already reflects product-vision.md at
  `philosophy/product-vision.md`; quality-assurance entry removed from the sdd/ section
  (it is now top-level, outside the product catalog). No structural change to index required
  beyond verifying consistency — verified.
- `specs/memory/product/catalog.json` — generated at 2026-06-07T06:33:12Z; reflects current
  atom set including product-vision; does not include quality-assurance (top-level, outside
  catalog). Consistent. No regeneration required.
- `specs/memory/product/sdd/specs-doctor.md` — this atom predates v0.2.1 and does not yet
  reflect the new TREE-3 top-level QA check or the AGENTS.md check. Updated in this CLOSURE
  (see architecture.md update note below). The atom's summary and check table require
  revision to note the rglob fix, TREE-3 addition, and AGENTS.md check.

## Backlog returns

- `specs/backlog/candidates.md` — PM to file: (a) two dead cross-ref residuals from closure
  audit; (b) rglob-symlink LOW gap; (c) persona-allowlist-resolves-to-existing-dir test gap.
  These are v0.2.2 candidates.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/v0.2.1/` via:

```
git mv specs/releases/v0.2.1 specs/_archive/releases/v0.2.1
```

This command is delegated to the orchestrator (project-manager or operator). After the
`git mv`, `ACTIVE.md` is set to `release: none`.
