---
slug: TECHSTACK
title: Tech Stack Memory
tldr: Python 3.12 Typer CLI; stdlib services; six entry harnesses as registry records (Claude, Codex, Kimi, Cursor, Devin, Copilot); closed marker set; strict gates.
summary: Part 1 carries the measured marker-set principle; Part 2 is the current language, dependency, runtime, model, testing, packaging and command contract.
tags: [tech-stack, dependencies, toolchain, constraints]
---
## Part 1 — Principles
### P-28 · We keep the pytest marker set closed and single-sourced: `pyproject.toml`'s `markers` equals `tests/conftest.py`'s `_KNOWN_MARKERS`, and `flaky`/`quarantine` are always among them.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k marker_set`.
ADR: none
Rationale: a marker known to one file and unknown to the other is a silent exclusion lane.
### P-30 · The version, the CHANGELOG section and the tag of a release come from release-please over Conventional Commits, and promote is merging its release PR; a candidate's closed trio lives in git at its CLOSURE commit, never in a copied candidate or archive directory.
Measured by: `pytest tests/contract/test_release_semver_canon.py tests/contract/test_ci_workflow_hygiene.py`.
ADR: 0021 (accepted)
Rationale: a hand-minted version and a hand-copied archive are two more writers of one fact each; the commit history already holds both.
## Part 2 — Implementation
### Snapshot
- Python `^3.12`, Poetry Core build, console entrypoints `dadaia` and `dadaia-workspace` (one callable); the version lives in `pyproject.toml` alone ([[pypi-distribution]]).
- Deps are Typer, Rich, PyYAML, Jinja2 and jsonschema plus an optional `claude-sdk` extra; everything else is stdlib, and no database exists — every state is a JSON or JSONL file.
- Codex, Kimi Code, Cursor, Devin and Copilot are operator-installed external CLIs, never Python deps, and the workspace runs no agent-execution runtime.
- Entry harnesses are single-sourced as `HARNESS_RECORDS` in `core/harness_registry.py` — Claude Code, Codex, Kimi Code, Cursor, Devin CLI, GitHub Copilot — one record each (directory, agent transcode, hook dialect) over the shared `.agents/` root; `dadaia certify` carries one `<harness>-live-probe` per record, SKIP `UNVERIFIED` when the binary is absent, no version floor.
- Layer-1 agent bodies are model-agnostic in source and receive `(model, effort)` at `public install`; Codex projections carry registry-derived Codex-native tier identity.
- Quality tooling is pytest with `pytest-cov`, `pytest-xdist`, `pytest-randomly` and `pytest-timeout`, Ruff, mypy `--strict`, import-linter, Hypothesis, Playwright and gitleaks; every cache is redirected by `pyproject.toml` (`addopts -p no:cacheprovider`, `[tool.ruff] cache-dir`, `[tool.mypy] cache_dir` → `../../.dadaia/tmp/<tool>-cache`), so the bare commands are the canonical ones and no per-command flag exists.
- The closed marker set is eight — unit, contract, integration, e2e, slow, tmp, flaky, quarantine (P-28).
- Mutation testing is `mutmut==3.7.0` in an optional Poetry group, absent from every push-path selector ([[QUALITY]]).
- `ci.yml` checks out at the default depth (the `security-review` job fetches depth 2 for the PR diff); `release.yml` and `secret-scan.yml` fetch full history for tag derivation and the whole-history secret scan — no job fetches history for a bug record's sake ([[QUALITY]]).
- Caches and artifacts live outside repos by configuration; the venv guard's one rule is venv-rooting, and a cache that still appears in a repo tree is moved to `.dadaia/reaped/` by the doctor's reaper ([[sdd-gate-v3]], [[workspace-doctor]]).

### Canonical commands

```bash
.dadaia/.venv/bin/dadaia --version
.dadaia/.venv/bin/python -m pytest
.dadaia/.venv/bin/dadaia ci preflight
.dadaia/.venv/bin/dadaia doctor
.dadaia/.venv/bin/dadaia public doctor
.dadaia/.venv/bin/dadaia certify --json
```

### Packaging

- Wheels and sdists exclude bytecode, and the canonical `public/` tree ships inside the `dadaia_workspace` package (`packages = [{include = "dadaia_workspace"}]`, no separate `include` entry), so a consumer install carries agents, skills, law, schemas, templates and scaffold.
- The capabilities payload is `dadaia-capabilities-v2`, and `dadaia certify` runs the deterministic check list against a live workspace.

### Dependencies

[[ARCHITECTURE]], [[QUALITY]], [[harness-claude-code]], [[harness-codex]], [[harness-kimi-code]].
