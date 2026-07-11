# CLOSURE — Release v0.1.77 — Central bind-resolution seam

**Shipped:** PR #151, squash-merged to main as `e002e7d9` (2026-07-11). All PR checks
green; post-merge main CI green.

## Delivered

- FR1: one canonical resolution order in `cli/_specs_resolution.py#resolve_context_for_cli`
  (explicit → `DADAIA_CONTEXT` → own session record → ancestry → first-ALIVE →
  self-hosting-slug terminal fallback), `context show` no-arg folded in (the
  cross-context incumbent-pointer scan retired — same context-global family as audit
  P1-1).
- FR2: 15 hardcoded lifecycle `--context "dadaia-workspace"` defaults retired to
  unset-resolves-bound (user-visible; explicit always wins).
- FR3: dynamic Typer-walk contract test (90 leaf commands, AST-reachability
  classification of 36 context/specs_dir params; 4 genuine non-resolver params
  correctly excluded) + executed-path CliRunner probes after a real bind + new
  zero-ignore import-linter contract `bind-resolution-seam-is-a-single-home`.
- FR4: resolution law pinned — removing the seam from any verb fails the contract.

## Dispositions

- Backlog `central-bind-resolution-seam` (family F2): **delivered**, archived.
- New backlog filed from the security review INFO:
  `20260711-context-name-allowlist-at-resolution-rungs` (P4 defense-in-depth).
- No open bugs consumed (F2 had no open bug events; its 8 historical reports were
  already terminal).

## Deviations

- PLAN's `typer.BadParameter`-on-exhaustion design was replaced by a terminal
  self-hosting-slug fallback: 47 pre-existing tests pin graceful degradation with
  exit-code 3 semantics in the never-onboarded workspace. QA verified first-ALIVE
  strictly precedes the literal (consumer workspaces never hit it) and the ordering is
  now directly unit-pinned (`tests/unit/cli/test_specs_resolution.py`, added from the
  QA LOW recommendation).

## Validations

- Suite 2,810 passed / 10 skipped (known LOW flake deselected + reproduced-as-registered).
- mypy --strict clean; ruff clean; lint-imports 10/10 contracts kept.
- QA APPROVED; security APPROVED (no control touched; traversal INFO routed to backlog).
