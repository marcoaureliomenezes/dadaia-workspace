# PLAN: v0.1.39 alpha-1 - SDD governance v2 taxonomy and workflow scope repair

**Status:** Aprovado
**Release ID:** v0.1.39
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

## Strategy

Ship the smallest release that safely advances the governance-v2 backlog and restores the
release-definition workflow path that blocked while defining this release.

## Work Plan

1. Add scoped-selection support for release-definition dynamic inputs.
   - Thread selected backlog/bug/audit identifiers into the release-definition workflow's
     context selection.
   - Keep generic `ContextSelector` behavior unchanged for workflows that do not provide
     scope.
   - Add integration coverage around injected context refs.

2. Implement the accepted per-class archive taxonomy.
   - Update path classification for `specs/backlog/_archive/**`,
     `specs/audits/_archive/**`, and `specs/bugs/_archive/**`.
   - Update scaffold/doctor expectations so these directories exist.
   - Add unit/contract coverage.

3. Update SDD artifacts.
   - Close the picked workflow bug if fixed.
   - Close the segmented review prompt bug if fixed.
   - Rewrite the backlog item to preserve only JSONL bug-events and audit-disposition
     residuals after taxonomy ships.
   - Run specs doctor and focused tests before closure.

4. Repair segmented review prompt guidance.
   - Resolve the active release segment from `ACTIVE.md`.
   - Include the concrete artifact directory in single-step lifecycle worker prompts.
   - Cover the prompt helper with a CLI skeleton regression.

## Validation

- Focused release-definition workflow tests.
- Focused gate-policy classification tests.
- Focused specs scaffold/doctor tests touched by the taxonomy.
- `ruff check --no-cache` and `mypy --strict` on changed Python files.
- `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs`.
- A real `dadaia lifecycle release define` smoke for `v0.1.39` scope after the selector fix,
  using a fresh run id and bounded harness configuration.

## Risks

- The selector fix must not narrow discovery steps like `release_scope`; only post-scope
  selected-item inputs should be exact.
- Introducing per-class `_archive` directories must not alter the shipped central release
  archive or consumed-backlog ledger behavior.
