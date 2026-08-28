---
slug: tech-stack
title: Tech Stack Memory
category: core
tldr: Python 3.12 Typer CLI; stdlib services; three entry harnesses (Claude Code, Codex, Kimi Code); one closed marker set; strict quality gates.
summary: Part 1 carries the measured marker-set principle; Part 2 is the current language, dependency, runtime, model, testing, packaging and command contract.
tags: [tech-stack, dependencies, toolchain, constraints]
---
## Part 1 — Principles
### P-28 · We keep the pytest marker set closed and single-sourced: `pyproject.toml`'s `markers` equals `tests/conftest.py`'s `_KNOWN_MARKERS`, and `flaky`/`quarantine` are always among them.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k marker_set`.
ADR: none
Rationale: a marker known to one file and unknown to the other is a silent exclusion lane.
## Part 2 — Implementation
### Snapshot
- Python `^3.12`, Poetry Core build, console entrypoint `dadaia`; the version lives in `pyproject.toml` alone ([[pypi-distribution]]).
- Deps are Typer, Rich, PyYAML, Jinja2, jsonschema, Mistune and openpyxl plus an optional `claude-sdk` extra; everything else is stdlib, and SQLite backs local telemetry.
- Codex and Kimi Code are operator-installed external CLIs, never Python deps, and the workspace runs no agent-execution runtime.
- Entry harnesses are single-sourced as `L1_ENTRY_HARNESSES` in `core/harness_registry.py` — Claude Code, Codex, Kimi Code — each with its own projection plus the shared `.agents/` root.
- Layer-1 agent bodies are model-agnostic in source and receive `(model, effort)` at `public install`; Codex projections carry registry-derived Codex-native tier identity.
- Quality tooling is pytest with `pytest-cov`, `pytest-xdist`, `pytest-randomly` and `pytest-timeout`, Ruff, mypy `--strict`, import-linter, Hypothesis, Playwright and gitleaks, with `-p no:cacheprovider` in addopts.
- The closed marker set is eight — unit, contract, integration, e2e, slow, tmp, flaky, quarantine (P-28).
- Mutation testing is `mutmut==3.7.0` in an optional Poetry group, absent from every push-path selector ([[quality-assurance]]).
- Caches and artifacts live outside repos, and the venv guard refuses an invocation that would write one in-tree ([[sdd-gate-v3]]).

### Canonical commands

```bash
.dadaia/.venv/bin/dadaia --version
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider
.dadaia/.venv/bin/dadaia doctor
.dadaia/.venv/bin/dadaia specs doctor
.dadaia/.venv/bin/dadaia public doctor
.dadaia/.venv/bin/dadaia certify --json
.dadaia/.venv/bin/dadaia panel --no-open
```

### Packaging

- Wheels and sdists exclude bytecode, and the canonical `public/` tree ships via the package include, so a consumer install carries agents, skills, law, schemas, templates and scaffold.
- The capabilities payload is `dadaia-capabilities-v2`, and `dadaia certify` runs the deterministic check list against a live workspace.

### Dependencies

[[architecture]], [[quality-assurance]], [[harness-claude-code]], [[harness-codex]], [[harness-kimi-code]].
