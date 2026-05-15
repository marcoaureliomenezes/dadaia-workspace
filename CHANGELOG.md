# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-14

### Added
- `dadaia` CLI: `init`, `context {create, list, show, activate, deactivate, promote, delete, use}`, `repos`, `public {stage, install, doctor}`, `doctor`, `academy`, `export`, `import`, `orchestrate {list, show, run, status, resume}`.
- Spec Context Project model (v4.0): multi-active contexts, single `is_primary` flag, JSON-backed state.
- Universal agentic assets: 6 agents (`product-engineer`, `software-architect`, `software-engineer`, `qa-engineer`, `devops-engineer`, `game-developer`), 17 skills, 4 commands, 2 rules.
- Cross-tool parity for Claude Code, OpenCode, Codex, and `.agents/`.
- Workspace portability: `dadaia export` / `dadaia import` with branch tracking.
- Multi-Agent Orchestration v0.1 — `workflows/` first-class asset type, durable run state (`manifest.json` + `events.jsonl`), 4 dispatchers (Claude/CLI/OpenCode/Codex), 2 seed workflows (`spec-refinement`, `tdd-cycle`).
- `input_contract` block in every agent frontmatter (Handoff Schema v1).
- `[partial]`/`[unsupported]` doctor status classification per runtime.
- CI workflow (`.github/workflows/ci.yml`) with lint, typecheck, test, pr-title jobs.
- Release workflow (`.github/workflows/release.yml`) with OIDC trusted publishing to PyPI.
- SDD Gate v2 (`sdd-spec-gate.sh`): gates edits to `repos/<primary_slug>/` (active Spec Context), requires `[-]` IN PROGRESS task marker in TASKS.md, meta-edit bypass for spec files (TASKS.md, PLAN.md, SPEC.md), fail-open on any internal error.
- Task State Contract (RF-CONV-006): 3-marker convention `[ ]`/`[-]`/`[x]` with `dadaia-task-manager` skill propagated to all 6 agents.
- Coverage gate: `--cov-fail-under=80`; current coverage 82%+ across unit + integration tests.

### Fixed
- BUG-002: `ctx-inject.sh` and `sdd-spec-gate.sh` now resolve `WORKSPACE_ROOT` via their own script path; no longer depend on git rev-parse or `$HOME`.
- BUG-003: `dadaia import` now rewrites absolute workspace paths in `.claude/settings.json`, `.codex/hooks.json`, and `.opencode/opencode.json` after extraction (`patch_json_paths` phase).
