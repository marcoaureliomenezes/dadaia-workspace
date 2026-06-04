# Closure: Release — v0.1.4.2

> **Status:** Aprovado
> **Release ID:** v0.1.4.2
> **Owner:** product-engineer
> **Closed:** 2026-06-04

## Summary

This release fixes the reported context, Codex orchestration, and implementation-review workflow bugs without bumping the package version beyond `0.1.4`.

The product now treats session-bound context as the active model across source, public assets, generated projections, and memory. Codex orchestration is truthful: Codex workflows are reference-only/manual unless the host conversation provides a real delegation tool. The development workflow now has a strict pre-implementation agreement gate and a post-implementation QA/code/security review gate before work can be marked done, pushed, opened as a PR, deployed, or closed.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-BUG-01 | Define allowed legacy primary-context exceptions | `c5ea9a4` |
| T-BUG-02 | Remove session-bind primary residue from CLI/source | `8450c29` |
| T-BUG-03 | Remove session-bind primary residue from public assets and memory | `ba27f00` |
| T-BUG-04 | Make Codex dispatcher capabilities truthful | `1acd32b` |
| T-BUG-05 | Align Codex-facing orchestration wording | `d994096` |
| T-BUG-06 | Add regression tests for both bugs | `67d82c3` |
| T-BUG-07 | Define strict implementation-review QA contract | `003b060` |
| T-BUG-08 | Align implementer and reviewer personas with the gate | `94ce2b4` |
| T-BUG-09 | Add regression tests for workflow gate contract | `ab4117e` |
| T-BUG-10 | Propagate assets and verify release | `bd6a6b6` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Legacy primary-context residue is limited to explicit migration cleanup | `rg -n "primary_context|is_primary|context promote|context activate" dadaia_workspace/public dadaia_workspace/cli dadaia_workspace/core dadaia_workspace/infrastructure specs/memory` | ```text\ndadaia_workspace/cli/commands/migrate.py:65:            if c["had_is_primary"]:\ndadaia_workspace/cli/commands/migrate.py:66:                typer.echo("    is_primary   (removed)")\ndadaia_workspace/cli/commands/migrate.py:71:    if plan.primary_context_exists:\ndadaia_workspace/cli/commands/migrate.py:72:        typer.echo("  DELETE .dadaia/states/primary_context.json")\n``` |
| Public assets propagated | `.dadaia/.venv/bin/dadaia public stage && .dadaia/.venv/bin/dadaia public install --target all --force` | ```text\npublic stage: 12 asset group(s) staged\npublic install: 176 asset(s) processed\n``` |
| Public projection doctor and privacy gate | `.dadaia/.venv/bin/dadaia public doctor` | ```text\n[ok] public-privacy\n[reference-only] codex:workflows/spec-refinement.workflow.md (installed, no workflow executor)\n``` |
| Specs doctor | `.dadaia/.venv/bin/dadaia specs doctor` | ```text\n0 error(s), 5 warning(s)\n``` |
| Unit test suite | `.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider -m "unit and not slow" tests/unit` | ```text\n1543 passed, 1 xpassed in 13.32s\n``` |
| Specs unit slice | `.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/features/specs/` | ```text\n96 passed in 2.94s\n``` |
| Source repo hygiene | `find . -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' -o -name '.dadaia' -o -name '.venv' -o -name 'test-results' -o -name 'playwright-report' -o -name 'coverage' \) -print && find . -name '.coverage' -print` | ```text\n(no output)\n``` |

## Drifts

### specs-doctor-warnings

**Description:** `dadaia specs doctor` exits with zero errors but reports existing warnings for four-segment release folder names, missing `specs/AGENTS.md`, and missing `specs/memory/product/catalog.json`.

**Resolution:** The warnings were not changed in this bugfix release because the operator explicitly required `v0.1.4.2` and the release scope was limited to the reported bugs, asset propagation, and validation. The zero-error exit satisfies the release gate.

**Memory updates:** None.

### codex-reference-only

**Description:** Codex workflows are installed but have no native workflow executor in the runtime projection.

**Resolution:** The release chose manual/reference-only Codex orchestration and made the dispatcher, public wording, memory, and doctor output truthful instead of simulating unsupported parallel agent execution.

**Memory updates:** `specs/memory/product/agent-orchestration.md`, `specs/memory/architecture.md`.

## Memory updates

- `specs/memory/product/context-management.md` — clarified that session binding is the active context mechanism and write authorization has no ALIVE fallback.
- `specs/memory/product/sdd-gate-v3.md` — clarified that production/release writes require `DADAIA_SESSION_ID` plus a matching session file; no workspace-scan fallback authorizes writes.
- `specs/memory/product/agent-orchestration.md` — added the pre-implementation agreement and post-implementation review/QA approval gate.
- `specs/memory/architecture.md` — added the architecture-level implementation review/QA gate invariant.
- `specs/memory/product/agent-comms.md` — no change: the handoff schema did not change.
- `specs/memory/tech-stack.md` — no change: the release did not add dependencies or runtime support.

## Backlog returns

- None.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/v0.1.4.2/` via `git mv`. `ACTIVE.md` will be updated to `release: none`.
