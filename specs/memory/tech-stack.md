---
slug: tech-stack
title: Tech Stack Memory
category: core
tldr: Python 3.12 CLI/library, stdlib local services, Typer/Rich, strict quality tools, and Claude/Codex/PI runtimes.
summary: >-
  Current language, dependency, runtime, model, testing, packaging, and command
  contracts for dadaia-workspace.
tags:
- tech-stack
- dependencies
- toolchain
- constraints
token_estimate: 545
last_updated: '2026-07-15'
release_origin: v0.2.5
---

## Language And Packaging

- Python `^3.12`; package/build metadata in `pyproject.toml` and `poetry.lock`.
- Poetry Core is the build backend; the installed console entrypoint is `dadaia`.
- Wheels/sdists exclude bytecode and include canonical public assets.
- PI and Codex are external operator-installed CLIs, not Python dependencies.

## Runtime Dependencies

| Package | Purpose |
|---|---|
| Typer + Rich | CLI parsing and output |
| PyYAML, Jinja2 | structured configuration and templates |
| jsonschema | handoff/schema validation |
| Mistune | in-memory Markdown rendering for the panel |
| openpyxl | known-repository catalog input |
| claude-agent-sdk extra | optional Claude SDK adapter only |

The panel, server registry, workspace state, and most services use the Python standard
library. SQLite backs local telemetry. Shell assets are limited to Git chokepoints:
`pre-commit-presence-gate.sh` and `pre-push-ci-gate.sh`; harness governance hooks are
Python or PI TypeScript projections.

## Agent Runtimes

- **Claude Code:** Layer-1 entry runtime; public agents/skills/rules and Python hooks.
- **Codex:** Layer-1 entry runtime and Layer-2 `codex exec` worker.
- **PI:** trusted Layer-1 entry runtime and Layer-2 `pi --mode json` worker.

Layer-2 Codex profiles use `gpt-5.5` at medium/high reasoning. PI profiles include
provider-qualified `openai-codex/gpt-5.5` at low/medium/high and the explicit optional
OpenRouter `moonshotai/kimi-k2.5:high` profile. Provider qualification is part of the
model contract.

Layer-1 agent model/effort comes from the selected agent-policy template plus operator
overrides. Layer-2 model/effort comes from workflow profiles and per-run policy.
The v0.2.5 live contract was certified with `codex-cli 0.144.4`; both headless exec
and TUI fired all four projected hook events.

## Quality Toolchain

- pytest with unit, contract, integration, e2e, slow, and tmp markers;
- Ruff format/lint;
- mypy strict with incremental cache disabled;
- import-linter architecture contracts;
- Hypothesis for properties;
- Playwright for panel browser journeys;
- gitleaks for secret scanning.

All caches and artifacts are disabled or redirected outside repositories. CI runs Linux
quality jobs, Windows/macOS cross-platform suites, repo hygiene, backlog doctor, PR/title
policy, security verdict gating, and browser tests. Contract coverage requires 80% in CI.

## Canonical Commands

```bash
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider
.dadaia/.venv/bin/dadaia specs doctor
.dadaia/.venv/bin/dadaia public doctor
.dadaia/.venv/bin/dadaia doctor
.dadaia/.venv/bin/dadaia lifecycle --help
.dadaia/.venv/bin/dadaia panel --no-open
```

Development lint/type commands run through the project Poetry environment when the full
dev dependency set is installed.

## Prohibitions

- No system Python for workspace commands.
- No repo-local venv, `.dadaia`, cache, coverage, Playwright report, or test-result tree.
- No secrets outside the operator-managed workspace-root `.env` or a runtime's external
  operator-managed OAuth store.
- No direct feature-to-infrastructure construction; use ports and `container.py`.

## Dependencies

[[architecture]], [[quality-assurance]], [[harness-claude-code]], [[harness-codex]],
[[harness-pi]].
