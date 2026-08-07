---
slug: tech-stack
title: Tech Stack Memory
category: core
tldr: Python 3.12 Typer CLI; stdlib services; four entry harnesses (Claude Code, Codex, PI, Kimi Code); strict quality gates.
summary: Current language, dependency, runtime, model, testing, packaging, and command contracts for dadaia-workspace.
tags: [tech-stack, dependencies, toolchain, constraints]
token_estimate: 420
last_updated: '2026-08-07'
release_origin: v0.3.0
---

## Snapshot

The session bootstrap injects only the top of this file — these bullets ARE the digest.

- Python `^3.12` · Poetry Core build · console entrypoint `dadaia` · version lives in `pyproject.toml` only (currently `0.5.0`).
- Deps: Typer + Rich (CLI), PyYAML, Jinja2, jsonschema, Mistune, openpyxl; optional `claude-sdk` extra. Everything else is stdlib; SQLite backs local telemetry. PI/Codex/Kimi Code are external operator-installed CLIs, never Python deps.
- Entry harnesses (the whole roster, single-sourced as `L1_ENTRY_HARNESSES` in `core/harness_registry.py`): **Claude Code**, **Codex**, **PI**, **Kimi Code**. Each gets its own projection (`.claude/`, `.codex/`, `.pi/`, `.kimi-code/`) plus the shared `.agents/` skills root; Kimi registers hooks via a managed block in the user-level `$KIMI_CODE_HOME/config.toml` since it has no project-level config. The workspace runs no agent-execution runtime of its own.
- Agent models: Layer-1 agent bodies are model-agnostic in source and receive `(model, effort)` at `public install` from the selected agent-policy template plus the operator overlay in `.dadaia/states/agent_model_policy.json`. Codex projections carry Codex-native `(model id × model_reasoning_effort)` tier identity, registry-derived.
- Quality: pytest (markers unit/contract/integration/e2e/slow/tmp, `-p no:cacheprovider` in addopts), Ruff format/lint, mypy `--strict` (incremental disabled), import-linter, Hypothesis, Playwright (panel), gitleaks. Contract coverage ≥80% in CI; caches/artifacts always live outside repos.
- Prohibitions: no system Python for workspace commands; no repo-local venv/`.dadaia`/cache/coverage trees; secrets only in the operator-managed root `.env` (or a runtime's external OAuth store); features reach infrastructure via ports + `container.py`, never directly.

## Canonical Commands

```bash
.dadaia/.venv/bin/dadaia --version
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider
.dadaia/.venv/bin/dadaia doctor
.dadaia/.venv/bin/dadaia specs doctor
.dadaia/.venv/bin/dadaia public doctor
.dadaia/.venv/bin/dadaia certify --json
.dadaia/.venv/bin/dadaia panel --no-open
```

Development lint/type commands run through the project Poetry environment when the full
dev dependency set is installed.

## Packaging Notes

- Wheels/sdists exclude bytecode (`**/__pycache__`, `*.pyc`, `*.pyo`); the canonical
  `public/` asset tree ships via the package include (`dadaia_workspace` package), so
  every consumer install carries agents, skills, the `DADAIA.md` law, schemas, templates,
  scaffold, plugin packs, and the consumer validation recipe.
- Agent model/effort comes from the selected agent-policy template plus operator
  overrides, resolved at `public install` and rendered into each projection.
- The capabilities payload is `dadaia-capabilities-v2`; `dadaia certify` runs the
  deterministic check list against a live workspace.

## Dependencies

[[architecture]], [[quality-assurance]], [[harness-claude-code]], [[harness-codex]],
[[harness-pi]], [[harness-kimi-code]].
