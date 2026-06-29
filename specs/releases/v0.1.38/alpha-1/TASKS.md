# TASKS: v0.1.38 alpha-1 - pi-agent-fourth-harness WS-PI-5

**Status:** Aprovado
**Release ID:** v0.1.38
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T1 - Retire standalone PI workspace context

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `repos/dadaia-pi-workspace/README.md`, workspace context state via `dadaia context dead`, `dadaia_workspace/features/spec_context/service.py`, `tests/integration/test_dead_review_gate.py`, `specs/bugs/context-dead-nonwritable-guard-rejects-standard-git-objects.md`, `specs/backlog/pi-agent-fourth-harness.md`, `specs/backlog/candidates.md`, `specs/releases/v0.1.38/alpha-1/**`
- **Acceptance:** The standalone repo has a committed deprecation pointer, `dadaia-pi-workspace` context is DEAD, the local checkout is absent, and `pi-agent-fourth-harness` is terminally consumed by v0.1.38.
- **Validation:** `pytest -p no:cacheprovider tests/integration/test_dead_review_gate.py -q` -> `6 passed`; `ruff check --no-cache` on touched implementation/test files -> `All checks passed!`; `mypy --strict dadaia_workspace/features/spec_context/service.py` -> `Success`; real `.dadaia/.venv/bin/python -m dadaia_workspace.cli.main context dead dadaia-pi-workspace --commit` -> context DEAD; `dadaia context show dadaia-pi-workspace --json` -> `"state": "dead"`; local checkout absent; standalone remote `main` at deprecation commit `4ffc2376666ba324a1ebf8c6bc8b387048e43719`.
