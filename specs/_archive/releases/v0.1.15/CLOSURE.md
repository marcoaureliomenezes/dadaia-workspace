# Closure: Release — v0.1.15

> **Status:** Aprovado
> **Release ID:** v0.1.15
> **Owner:** product-engineer
> **Closed:** 2026-06-20

## Summary

v0.1.15 ships the Codex-side deterministic lifecycle foundation for dadaia-workspace. The new `dadaia lifecycle` surface gives Python ownership of state transitions, preflight, blocked/resume, hygiene policy, report workflow artifacts, semantic review gates, and scoped Codex worker execution.

The release is intentionally foundational. It does not automate every backlog/release/implementation/review workflow body yet; it establishes the reusable runtime, state, gate, hygiene, and adapter primitives those workflows must call.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-015-00 | Release approval, active release, and implementation branch | `0e861af` |
| T-015-01 | Lifecycle core models | `098d772` |
| T-015-02 | Hygiene models and SlopPolicy | `320aaf8` |
| T-015-03 | Runtime file and agent runtime protocols | `80ddd40` |
| T-015-04 | Filesystem runtime-file adapters | `463e52e` |
| T-015-05 | Shared hygiene status and TTL reconciliation | `5ac4f05` |
| T-015-06 | Boundary-safe cleanup and preservation rules | `aa9c40d` |
| T-015-07 | Hygiene snapshot and high-volume scan test | `13e3747` |
| T-015-08 | Lifecycle state machine | `14f4b30` |
| T-015-09 | Semantic handoff gate validators | `3988ea8` |
| T-015-10 | Preflight service and blocked/resume state | `91fc2c6` |
| T-015-11 | Lifecycle run-state store | `9682c88` |
| T-015-12 | Lifecycle command group | `1d24bca` |
| T-015-13 | Status, preflight, and hygiene CLI behavior | `82c97d8` |
| T-015-14 | Report workflow proof | `e611526` |
| T-015-15 | Guarded skeleton commands | `44d95eb` |
| T-015-16 | Fake AgentRuntimePort tests | `1d08f84` |
| T-015-17 | Codex exec adapter decision and implementation | `3f76f05` |
| T-015-18 | Scoped prompt builder and write allowlist contract | `b3065b1` |
| T-015-19 | Blocked push/resume regression | `04ec27d` |
| T-015-20 | Review gate integration | `37c9417` |
| T-015-21 | Temp workspace lifecycle smoke | `d76f8da` |
| T-015-22 | Final validation | `0b8d510` |
| T-015-23 | CLOSURE, memory, and disposition sweep | `ca5ba47` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Formatting and lint | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m ruff format --check . && /home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m ruff check --no-cache .` | ```text
580 files already formatted
All checks passed!
``` |
| Production strict typing | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m mypy --strict dadaia_workspace` | ```text
Success: no issues found in 244 source files
``` |
| Full test suite | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -p no:cacheprovider` | ```text
3308 passed, 10 skipped in 265.63s (0:04:25)
``` |
| Lifecycle smoke and performance subset | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/test_lifecycle_asymmetry_map.py tests/contract/test_source_repo_hygiene.py tests/e2e/test_lifecycle_engine_smoke.py tests/performance/test_lifecycle_hygiene_scan.py` | ```text
7 passed in 62.45s (0:01:02)
``` |
| Specs doctor | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m dadaia_workspace specs doctor --specs-dir specs --json` | ```text
"summary": {"errors": 0, "warnings": 18}
``` |
| Public projection doctor | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m dadaia_workspace public doctor` | ```text
[ok] opencode:opencode.json
[ok] public-privacy
[ok] model-resolution
``` |
| Hygiene performance guard | `tests/performance/test_lifecycle_hygiene_scan.py` | ```text
baseline: 122 reports, 295 handoffs, 437724 tmp files
limits: elapsed < 90s, RSS delta < 96 MiB, content reads limited to handoffs
``` |
| T-015-21 QA gate | QA handoff by qa-engineer | `d76f8da` |
| T-015-22 QA gate | QA handoff by qa-engineer | `0b8d510` |

## Drifts

### lifecycle-asymmetry-map

**Description:** Final full pytest found that the new `features/lifecycle` package was absent from the contract README lifecycle-asymmetry coverage map.

**Resolution:** Added a grep-verified `lifecycle` row with real tests for delete/orphan, dirty input, and missing dependency/absent evidence paths. QA initially rejected aspirational test names; the row was corrected to existing test definitions.

**Memory updates:** None. This is a test-contract inventory correction, not product behavior.

### public-opencode-projection-drift

**Description:** `dadaia public doctor` reported `opencode:opencode.json` drift in the workspace-root generated projection.

**Resolution:** Ran `dadaia public install --target opencode`, which refreshed the generated workspace projection outside the source repo. `public doctor` then passed.

**Memory updates:** None. The generator behavior did not change.

### repo-local-claude-residue

**Description:** QA found ignored repo-local `.claude/settings.local.json` residue inside the source repo root, violating repo hygiene.

**Resolution:** Removed only the generated `.claude/settings.local.json` file and the empty `.claude/` directory. Source repo ignored-status then showed only the intentional README diff.

**Memory updates:** None. This was local generated residue, not product truth.

### broad-tests-strict-mypy-is-not-the-current-gate

**Description:** The broad command `mypy --strict dadaia_workspace tests` fails on pre-existing untyped legacy tests.

**Resolution:** The release gate used `mypy --strict dadaia_workspace` for production code and strict mypy on the affected validation files. The full test suite passed. No release code was weakened.

**Memory updates:** None. Existing typing debt remains outside this release.

## Memory updates

- `specs/memory/product/sdd/lifecycle-foundation.md` — new atom for the Codex lifecycle foundation, covering CLI surface, Python-owned state, semantic gates, hygiene, blocked/resume, and Codex runtime boundary.
- `specs/memory/product/index.md` and `specs/memory/product/catalog.json` — regenerated so the lifecycle atom is discoverable.
- `specs/memory/architecture.md` — updated CLI/features inventory to include `lifecycle`.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — updated current governance truth for lifecycle preflight, blocked/resume, and semantic gates.
- `specs/memory/tech-stack.md` — no change: release added no dependency and kept Codex integration exec-backed.
- `specs/memory/quality-assurance.md` — no change: validation behavior is captured by current tests and this closure; QA memory policy did not change.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/codex-push-policy-blocks-required-release-preflight.md` | bug | `Closed` | T-015-19 commit `04ec27d` and `tests/integration/test_lifecycle_push_preflight.py` |
| `specs/bugs/lifecycle-run-store-rejects-self-hosting-workspace-root.md` | bug | `Closed` | T-015-11 commit `9682c88` and run-store regression test |
| `specs/backlog/sdd-governance-v2-agents-lifecycle.md` | backlog | `CONSUMED — v0.1.15` | Lifecycle foundation slice delivered; remaining governance-v2 scope stays future backlog |
| `specs/backlog/workspace-sanitization.md` | backlog | `DELIVERED — v0.1.15` | Lifecycle hygiene policy, snapshots, cleanup, and performance evidence delivered |

## Backlog returns

- `specs/backlog/candidates.md` ← Future workflow bodies: backlog definition, release definition/review, implementation+review, closure/archive as Python routines that call bounded agent runtimes through `AgentRuntimePort`.
- `specs/backlog/candidates.md` ← Remaining governance-v2 scope from `sdd-governance-v2-agents-lifecycle.md`: roster/taxonomy/JSONL bug events/researcher relay not delivered by this foundation release.

## Archive decision

**MOVE** — release directory was moved to `specs/_archive/releases/v0.1.15/` via `git mv`. `specs/releases/ACTIVE.md` was reset to `release: none` and `phase: none`.
