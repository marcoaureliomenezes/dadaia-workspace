# Closure: Release - v0.1.38 alpha-1

> **Status:** Aprovado
> **Release ID:** v0.1.38
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Closed:** 2026-06-29

## Summary

v0.1.38 alpha-1 closes the final PI fourth-harness residual: the standalone `dadaia-pi-workspace` context is retired, its remote history remains intact, and the last backlog item is terminally delivered.

The release also fixed the context-retirement blocker found during the real `dead()` path. Context retirement now handles normal git-owned read-only object files without requiring manual chmod cleanup.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T1 | Retire standalone PI workspace context and close WS-PI-5 | `a5f45256bcb3211518707dc371554a4a48590f31` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Focused context-dead regression tests | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/integration/test_dead_review_gate.py -q` | ```text
6 passed in 1.40s
``` |
| Touched implementation lint | `.dadaia/.venv/bin/python -m ruff check --no-cache repos/dadaia-workspace/dadaia_workspace/features/spec_context/service.py repos/dadaia-workspace/tests/integration/test_dead_review_gate.py` | ```text
All checks passed!
``` |
| Strict typing for changed context service | `.dadaia/.venv/bin/python -m mypy --strict repos/dadaia-workspace/dadaia_workspace/features/spec_context/service.py` | ```text
Success: no issues found in 1 source file
``` |
| Real standalone context retirement | `.dadaia/.venv/bin/python -m dadaia_workspace.cli.main context dead dadaia-pi-workspace --commit` | ```text
Context 'dadaia-pi-workspace' is now DEAD
``` |
| Standalone context state | `.dadaia/.venv/bin/dadaia context show dadaia-pi-workspace --json` | ```text
"state": "dead"
``` |
| Standalone checkout removed | `test ! -e repos/dadaia-pi-workspace && echo absent` | ```text
absent
``` |
| Standalone remote keeps deprecation pointer | `git ls-remote https://github.com/marcoaureliomenezes/dadaia-pi-workspace refs/heads/main` | `4ffc2376666ba324a1ebf8c6bc8b387048e43719` |
| Release spec health | `.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` | ```text
[ok] overall: 0 error(s), 17 warning(s)
``` |

## Drifts

### context-dead-readonly-git-objects

**Description:** The planned `context dead dadaia-pi-workspace --commit` path exposed a pre-existing bug: `dead()` rejected standard git object files that are user-owned but not owner-writable.

**Resolution:** `dead()` now removes the context checkout with `shutil.rmtree(..., onexc=...)`; the retry handler restores owner write permission for normal user-owned read-only files and retries the remove operation.

**Memory updates:** `specs/memory/product/platform/context-management.md`.

## Memory updates

- `specs/memory/product/platform/context-management.md` - updated current `dead()` behavior for normal read-only git object cleanup.
- `specs/memory/architecture.md` - no change: release did not alter subsystem boundaries.
- `specs/memory/tech-stack.md` - no change: release did not alter dependencies or tooling.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/pi-agent-fourth-harness.md` | backlog | `DELIVERED - v0.1.38` | `a5f45256bcb3211518707dc371554a4a48590f31` |
| `specs/bugs/context-dead-nonwritable-guard-rejects-standard-git-objects.md` | bug | `Closed` | `a5f45256bcb3211518707dc371554a4a48590f31` |

## Backlog returns

No new backlog items were discovered during this release.

## Archive decision

**KEEP** - this is an alpha segment. Per segment policy, the full archive move is deferred to the shipping `rc-N` closure.
