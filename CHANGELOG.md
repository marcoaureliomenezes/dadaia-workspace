# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] — 2026-05-23

### Added
- 21-agent universal topology: ai-engineer, software-engineer-python, software-engineer-node, data-engineer, data-analyst, data-architect (6 new personas since 0.1.0); all agents carry TOML projections for Codex.
- Codex orchestration parity: `_install_codex_agents()` generates `.codex/agents/*.toml` per agent with model mapping (Claude→Codex identifiers); `_install_codex_rules()` projects only frontmatter-bearing rules; `CodexAgentDispatcher` with parallel best-effort dispatch; doctor checks D-CX-1..5 for Codex drift.
- Handoff schema v1.1: `scope`, `metrics`, `findings[].detail_md`, `findings[].fix_recommendation` fields; CLI hard-error on missing `findings[]`; `dadaia reports lint` subcommand for orphan/oversized/missing-fields detection.
- Bug reporting infrastructure: `bug_reporter.py`, `.dadaia/bugs/reported.json` persistent store, CLI exception handler via `_safe_app()`, doctor persistence via `report_doctor_finding()`, open-bug surface during `dadaia specs` release creation.
- Doctor `[warn] git-dirty` check: detects uncommitted edits in `public/` working tree (blind spot for the doctor diff).
- Workspace panel r5: 7-tab canonical order (Projects, Agents, Workflows, Sessions, Reports, Academy, Settings), Projects tab redesign, Reports tab, Academy tab (infrastructure), logo redesign, dark-mode token coverage.
- DEV workspace self-reference section in `dadaia-workspace-dev-guardrail.md` (4 invariants for the editable-install loop).
- Spec-refinement workflow v0.3.0: `research_evidence` stage (researcher) added before `discovery`; `spec_write` stage post-synthesis.
- `dadaia public doctor`: `[not-applicable]` status for logical type mismatches (e.g. workflows in Codex runtime); codex rules filter (behavioral prose rules excluded).
- Runtime codex adapter skills (`runtime/codex/design-ctx/SKILL.md`, `runtime/codex/frontend-ctx/SKILL.md`) for plugin-scoped Codex surface.
- Shared skills: `frontend-design`, `frontend-implementation-quality`, `design-report-quality-gate`, `design-reference-research`, `ux-ui-review`.

### Fixed
- CLAUDE.md is now a 1-line stub delegating to AGENTS.md (T-41); no longer a source copy — reduces noise in consumer repos.
- 19 pre-existing test failures resolved: schema v1.1 fixture gaps, stale model identifiers in test fixtures (`claude-sonnet-4-5`→`claude-sonnet-4-6`), T-41 CLAUDE.md stub invariant, stale EXPECTED_SKILLS set, `commands/` staging dir removal, behavioral-prose rule excluded from `.codex/rules/` projection, workflow v0.3.0 stage ordering in e2e test.
- 4 `dadaia context deactivate` bugs: git subprocess upstream tracking, service layer error handling.
- Init legacy resolver replaced with `resolve_workspace_root_for_init`; no longer errors on un-initialized workspaces.
- CSP `script-src` unsafe-inline replaced with SHA-256 hash in panel server.
- SQLite dead tables dropped via migration 6; telemetry service hardened.
- Exit code 3 on uninitialized workspace for `dadaia reports validate` (workspace resolver moved inside try).

### Changed
- All agents default to `claude-sonnet-4-6` (ADR-X4); ai-engineer moved from Opus to Sonnet; researcher uses `claude-haiku-4-5-20251001`.
- `AGENTS.md` is the canonical guardrail file; CLAUDE.md is a 1-line pointer (Option C / T-41).
- Skills split: 16 universal skills after removing game-*, devops-gitflow-governance, devops-deploy-strategies, architect-*, github-actions-pipelines, security-audit-protocol.

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
