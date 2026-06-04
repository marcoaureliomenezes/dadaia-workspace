# Closure: Release — v0.1.4.1

> **Status:** Aprovado
> **Release ID:** v0.1.4.1
> **Owner:** product-engineer
> **Closed:** 2026-06-04

## Summary

This consolidation release completed the agent architecture hardening track:
panel auth hardening was folded in, public agent assets were cleaned, handoff
schema instructions were aligned with the schema, the SDD gate was hardened, and
the public asset chain was propagated across supported runtimes.

The release did not change the published package version. Two critical bugs
remain open and are intentionally moved to the next release: session-bound
context residue in CLI/source/memory, and Codex orchestration parity wording vs
runtime behavior.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-HARD-00 | Merge hardening/panel-auth-review branch | `c6dac30` |
| T-HARD-01 | Fix sdd-spec-gate.sh context-resolution chain | `04336dc` |
| T-HARD-02 | Purge retired activate/primary refs from public assets | `04336dc` |
| T-HARD-03 | Align handoff emitter with bare 64-hex schema | `07f949c` |
| T-HARD-04 | Fix broken refs, language uniformity, scope blocks | `e88f500` |
| T-HARD-05 | Add tmp fast-allow and multiple [-] warning | `07f949c` |
| T-HARD-06 | Tighten allowlists and remove consumer-specific content | `e88f500` |
| T-HARD-11 | Propagate asset chain and verify acceptance criteria | `1a8bfa9` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Asset stage | `DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=sess_be12771f DADAIA_MODE=SPEC .dadaia/.venv/bin/dadaia public stage` | ```text\n✓ 12 asset group(s) staged\n``` |
| Asset install | `DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=sess_be12771f DADAIA_MODE=SPEC .dadaia/.venv/bin/dadaia public install --target all --force` | ```text\n✓ 176 asset(s) processed\n``` |
| Public doctor | `DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=sess_be12771f DADAIA_MODE=SPEC .dadaia/.venv/bin/dadaia public doctor` | ```text\n[ok] public-privacy\n``` |
| Unit suite | `source /home/marco/workspace/dadaia/.dadaia/.venv/bin/activate && poetry run pytest -q -p no:cacheprovider -m "unit and not slow" tests/unit` | ```text\n1549 passed, 1 xpassed\n``` |
| Specs unit tests | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/features/specs/` | ```text\n96 passed\n``` |
| Specs doctor | `DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=sess_be12771f DADAIA_MODE=SPEC .dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` | ```text\n0 error(s), 4 warning(s)\n``` |
| Handoff schema round-trip | `DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=sess_be12771f DADAIA_MODE=SPEC .dadaia/.venv/bin/dadaia reports validate .dadaia/tmp/t-hard-11/handoff-roundtrip.json` | ```text\nVALID   .dadaia/tmp/t-hard-11/handoff-roundtrip.json\nSummary: 1 valid, 0 invalid (of 1 files)\n``` |
| Repo hygiene | `find /home/marco/workspace/dadaia/repos/dadaia-workspace -maxdepth 2 \( -name .venv -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache -o -name test-results -o -name playwright-report -o -name coverage -o -name .coverage \) -print` | ```text\n(no output)\n``` |

## Drifts

### codex-projection-validation

**Description:** T-HARD-11 exposed additional Codex projection correctness issues:
Codex hooks needed nested hook JSON, `ctx-inject.sh` needed JSON output for
Codex `UserPromptSubmit`, forced Codex installs needed to remove stale generated
agents/workflows, and Codex `apply_patch` needed target-path parsing in the gate.

**Resolution:** Implemented and tested these projection/gate fixes as part of
T-HARD-11 because they were required for a clean propagated asset chain.

**Memory updates:** `specs/memory/product/public-asset-distribution.md`,
`specs/memory/product/sdd-gate-v3.md`, `specs/memory/architecture.md`.

### specs-doctor-session-bind-residue

**Description:** The exact no-argument `dadaia specs doctor` command still fails
to resolve specs and tells the operator to run the removed
`dadaia context activate <name>` verb. This is part of the open critical bug
`session-bind-primary-residue`.

**Resolution:** Used `--specs-dir repos/dadaia-workspace/specs` to validate the
current release structure with zero errors. The next release owns the no-arg CLI
fix and the remaining primary-context cleanup.

**Memory updates:** none in this release beyond documenting the current gate and
asset behavior.

### poetry-repo-venv

**Description:** Running `poetry run` without an activated workspace venv caused
Poetry to create a forbidden repo-local `.venv` and collection failed because
the environment lacked project dependencies.

**Resolution:** Removed the generated `.venv`, activated the workspace venv, and
reran the exact `poetry run pytest ...` command successfully without leaving
forbidden repo artifacts.

**Memory updates:** none.

## Memory updates

- `specs/memory/product/public-asset-distribution.md` — updated Codex hook JSON
  projection and forced stale projection cleanup behavior.
- `specs/memory/product/sdd-gate-v3.md` — updated RULE F, fail-closed production
  behavior for missing session identity, and Codex `apply_patch` path parsing.
- `specs/memory/architecture.md` — updated gate architecture and path-scope
  enforcement summary.
- `specs/memory/tech-stack.md` — no change: release did not change dependencies.

## Backlog returns

- `specs/bugs/session-bind-primary-residue.md` — carried into the next release.
- `specs/bugs/codex-agent-orchestration-mismatch.md` — carried into the next release.

## Archive decision

**MOVE** — release directory will be moved to
`specs/_archive/releases/v0.1.4.1/` via `git mv`. `ACTIVE.md` will point to the
next bug-fix release.
