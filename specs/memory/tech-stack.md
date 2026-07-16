---
slug: tech-stack
title: Tech Stack Memory
category: core
tldr: Python 3.12 Typer CLI; stdlib services; Claude L1 + Codex/PI dual-layer runtimes; strict quality gates.
summary: Current language, dependency, runtime, model, testing, packaging, and command contracts for dadaia-workspace.
tags: [tech-stack, dependencies, toolchain, constraints]
token_estimate: 450
last_updated: '2026-07-16'
release_origin: v0.2.5
---

## Snapshot

The session bootstrap injects only the top of this file — these bullets ARE the digest.

- Python `^3.12` · Poetry Core build · console entrypoint `dadaia` · version lives in `pyproject.toml` only.
- Deps: Typer + Rich (CLI), PyYAML, Jinja2, jsonschema, Mistune, openpyxl; optional `claude-sdk` extra. Everything else is stdlib; SQLite backs local telemetry. PI/Codex are external operator-installed CLIs, never Python deps.
- Runtimes: **Claude Code = Layer-1 only** (a `claude-*` id is never a Layer-2 worker); **Codex** and **PI** are Layer-1 entries AND Layer-2 workers (`codex exec`, `pi --mode json`); `fake` is the deterministic test adapter. This list is set-equal to `AgentRuntimeKind` (`core/models/lifecycle.py`).
- Layer-2 models: Codex profiles `gpt-5.5` (medium/high reasoning); PI profiles provider-qualified `openai-codex/gpt-5.5` (low/medium/high) plus the explicit opt-in OpenRouter `moonshotai/kimi-k2.5:high`. Provider qualification is part of the model contract.
- Quality: pytest (markers unit/contract/integration/e2e/slow/tmp, `-p no:cacheprovider` in addopts), Ruff format/lint, mypy `--strict` (incremental disabled), import-linter, Hypothesis, Playwright (panel), gitleaks. Contract coverage ≥80% in CI; caches/artifacts always live outside repos.
- Prohibitions: no system Python for workspace commands; no repo-local venv/`.dadaia`/cache/coverage trees; secrets only in the operator-managed root `.env` (or a runtime's external OAuth store); features reach infrastructure via ports + `container.py`, never directly.

## Canonical Commands

```bash
.dadaia/.venv/bin/dadaia --version
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider
.dadaia/.venv/bin/dadaia doctor
.dadaia/.venv/bin/dadaia specs doctor
.dadaia/.venv/bin/dadaia public doctor
.dadaia/.venv/bin/dadaia lifecycle --help
.dadaia/.venv/bin/dadaia panel --no-open
```

Development lint/type commands run through the project Poetry environment when the full
dev dependency set is installed.

## Packaging Notes

- Wheels/sdists exclude bytecode (`**/__pycache__`, `*.pyc`, `*.pyo`); the canonical
  `public/` asset tree ships via the package include (`dadaia_workspace` package), so
  every consumer install carries agents, skills, rules, fragments, personas, schemas,
  plugin packs, and the consumer validation recipe.
- Layer-1 agent model/effort comes from the selected agent-policy template plus operator
  overrides; Layer-2 model/effort comes from workflow profiles and per-run policy.
- The v0.2.5 live contract was certified with `codex-cli 0.144.4`; both headless exec
  and TUI fired all four projected hook events.

## Dependencies

[[architecture]], [[quality-assurance]], [[harness-claude-code]], [[harness-codex]],
[[harness-pi]].
