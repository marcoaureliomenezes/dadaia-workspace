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
Measured by: `pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k marker_set`.
ADR: none
Rationale: a marker declared in one file and unknown in the other becomes a silent exclusion lane.
## Part 2 — Implementation
### Snapshot
- Python `^3.12` · Poetry Core build · console entrypoint `dadaia` · the version lives in `pyproject.toml` and nowhere else ([[pypi-distribution]]).
- Deps: Typer + Rich (CLI), PyYAML, Jinja2, jsonschema, Mistune, openpyxl; optional `claude-sdk` extra. Everything else is stdlib; SQLite backs local telemetry. Codex and Kimi Code are external operator-installed CLIs, never Python deps.
- Entry harnesses, single-sourced as `L1_ENTRY_HARNESSES` in `core/harness_registry.py`: **Claude Code**, **Codex**, **Kimi Code**. Each gets its own projection (`.claude/`, `.codex/`, `.kimi-code/`) plus the shared `.agents/` skills root; Kimi registers hooks via a managed block in the user-level `$KIMI_CODE_HOME/config.toml`. The workspace runs no agent-execution runtime of its own.
- Agent models: Layer-1 agent bodies are model-agnostic in source and receive `(model, effort)` at `public install` from the selected agent-policy template plus the operator overlay in `.dadaia/states/agent_model_policy.json`. Codex projections carry Codex-native `(model id × model_reasoning_effort)` tier identity, registry-derived.
- Quality: pytest with `pytest-cov`, `pytest-xdist` (`-n auto` in CI and the local preflight), `pytest-randomly` and `pytest-timeout` (per-tier defaults applied at collection, P-21); the closed marker set is eight — unit/contract/integration/e2e/slow/tmp/flaky/quarantine (P-28) — and `-p no:cacheprovider` is in addopts. Ruff format/lint, mypy `--strict` (incremental disabled), import-linter, Hypothesis, Playwright (panel), gitleaks. Mutation testing is `mutmut==3.7.0` in the optional Poetry group `[tool.poetry.group.mutation]`, absent from every push-path selector ([[quality-assurance]]). Caches and artifacts always live outside repos, and the venv guard refuses a `pytest`/`ruff`/`mypy` invocation that would write one in-tree ([[sdd-gate-v3]]).
- Prohibitions: no system Python for workspace commands; no repo-local venv/`.dadaia`/cache/coverage trees; secrets only in the operator-managed root `.env` or a runtime's external OAuth store; features reach infrastructure via ports and `container.py` ([[architecture]] P-01, P-08).
- These bullets stay at the top of Part 2: `hooks/ctx_inject.py` injects only the leading lines of this atom as the once-per-session tech digest.

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

Development lint and type commands run through the project Poetry environment when the full dev
dependency set is installed.

### Packaging

Wheels and sdists exclude bytecode (`**/__pycache__`, `*.pyc`, `*.pyo`); the canonical `public/`
asset tree ships via the package include, so every consumer install carries agents, skills, the
`DADAIA.md` law, schemas, templates, scaffold and the consumer validation recipe. The capabilities
payload is `dadaia-capabilities-v2`; `dadaia certify` runs the deterministic check list against a
live workspace.

### Dependencies

[[architecture]], [[quality-assurance]], [[harness-claude-code]], [[harness-codex]],
[[harness-kimi-code]].
