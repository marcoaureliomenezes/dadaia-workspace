# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Panel HTTP handler: enforce Bearer auth on workspace-sensitive routes that were previously served by the unauthenticated dispatch loop — `/reports/<path>`, `/api/panel-status`, `/api/contexts`, `/memory/<slug>/<path>`, `/memory-view/<slug>/<path>` — whenever the panel is NOT loopback-bound (defense in depth; loopback keeps the zero-friction local default). (F-01/F-02/F-04)
- Scaffolder renders templates with a Jinja2 `SandboxedEnvironment`, blocking template access to Python internals. (F-03)
- `GitSubprocessClient.clone` refuses unsafe URLs (`ext::` transport and option-injection via a leading `-`) before invoking git. (F-05)

## [0.1.9] — 2026-06-09

### Changed
- Completed the layering law for process execution: `features/` modules no longer import
  `subprocess` directly. New `ProcessRunner` Protocol (`core/protocols/process_runner.py`)
  with production adapter `infrastructure/subprocess_runner.py`; consumed via DI by
  `import_`, `ci_preflight`, `specs/doctor`, and `server_registry`. New import-linter
  contract `features-no-subprocess` enforces it in CI.
- `container.py` platform branching now reads the `PLATFORM` capability singleton instead
  of an inline `sys.platform` comparison.
- Agent persona parity pass: `[SCOPE ERROR]` redirect block present in all 9 core personas;
  duplicated report-emission prose deduplicated to the `workspace-protocol §4` rule;
  vestigial `opencode_model` frontmatter keys removed; `dev-server-registry` skill wired to
  `software-engineer`; `ai-context-engineering` I1 schema reference refreshed.
- Agent model assignments retiered: `claude-fable-5` for product-engineer, qa-engineer,
  ai-engineer, software-architect, and project-auditor; `claude-opus-4-8` for
  software-engineer, security-reviewer, and code-reviewer.

### Fixed
- Spec/memory fidelity: all 34 confirmed findings of the 2026-06-09 drift audit resolved —
  memory atoms now document the real doctor check codes (`LOCK-NEW`/`INV-4`/`INV-5`/
  `SENTINEL-GC`), the Python-hook SDD gate (bash scripts described as legacy fallback only),
  the hard-gated 3-OS CI matrix, the full 21-subcommand CLI and 21-protocol inventory, the
  actual `specs doctor` check-ID set (SPEC-DOC 001–009/012/016, TREE-1..7 + TREE-5M), the
  correct project-manager model, the 18-skill count, and a roster without the phantom
  `researcher` agent. Archived 0.1.6 CLOSURE backfilled to structural doctor compliance.

## [0.1.8] — 2026-06-09

### Added
- **Cross-platform support (Linux / macOS / Windows).** `core/platform.py` platform-detection seam
  (sole `sys.platform` call site) + a port/adapter boundary for OS-sensitive domains: file locks
  (fcntl / msvcrt), telemetry refresh lock, file permissions (chmod / `icacls`), process probe, and
  signals/shutdown. New `dadaia_workspace/hooks/` Python governance package replaces the bash hooks
  so SDD governance is enforced on stock Windows (no Git Bash required). 3-tier resilience contract
  (fail-loud security / degrade-with-log / unsupported-at-construction). `import-linter` contracts
  enforce the layering law in CI.
- Phased 3-OS CI matrix: an importability-smoke job (Windows + macOS) plus Windows/macOS unit and
  contract legs (allow-fail during graduation; Ubuntu remains the hard gate).

### Changed
- `Operating System :: OS Independent` classifier corrected to `Operating System :: POSIX :: Linux`
  until the 3-OS CI matrix graduates to a hard gate.
- All text I/O now specifies `encoding="utf-8"` (Windows cp1252 corruption fix); the JSON stores
  route through a single `_atomic_write_text` chokepoint using `os.replace`.
- venv executable paths resolved via the platform seam (`Scripts/python.exe` on Windows).

### Fixed
- The CLI is now importable on Windows: the unconditional top-level `import fcntl` in the locking and
  telemetry modules (which crashed every `dadaia` invocation at import) is removed and delegated to
  platform adapters.
- Windows security no-ops closed: the panel auth token is owner-only via `icacls` or the panel
  refuses to start (Tier-1, CWE-732); `/proc` scans and `os.getuid` degrade safely off-Linux.

## [0.1.4] — 2026-06-03

### Added
- Executable pytest taxonomy (`unit`/`contract`/`integration`/`e2e`/`slow`/`tmp` markers), a `tests/contract/**` public-contract layer, and a `tests/tmp/**` quarantine excluded from default collection (`test-suite-architecture`).

### Changed
- Coverage instrumentation removed from default pytest `addopts` (fast local default); coverage now enforced only by an explicit CI job. CI split into per-layer jobs (lint, typecheck, unit-fast, contract-coverage, integration, e2e-python, e2e-panel).

### Security
- Removed the last hardcoded private identifiers from shipped source: the public-privacy denylist no longer embeds operator-specific values. Terms are now loaded at runtime from outside the published package (`$DADAIA_PRIVACY_DENYLIST` or `<repo_root>/.dadaia/states/privacy_denylist.json`); the library ships with an empty default (dev-guardrail rule #4).
- Purged residual private identifiers from the full git history and genericized changelog entries that previously enumerated them.

## [0.1.3] — 2026-06-03

### Security
- Removed two private academy modules (12 files) from the published wheel — they contained private-infrastructure operational docs.
- Purged private project identifiers (admin IP, hostname, and internal project/infrastructure slugs) from library source, tests, and fixtures; replaced with generic placeholders throughout.
- Removed hardcoded personal absolute paths (`/home/<user>/…`) from tests and fixtures.
- Re-seeded `sessions_seeded.sqlite` telemetry fixture to strip private session data.
- Genericized a private example in `core/workspace_resolver.py` docstring (shipped source).
- Neutralized canonical assets for open-source consumers: `public/data/AGENTS.md` language default changed to language-neutral; removed leaked operator-infra examples from the `dadaia-grill-me` skill.
- Trimmed bloated canonical rules to concise imperative form: `dadaia-workspace-dev-guardrail` 134→63 lines, `tmp-file-guardrail` 79→47 lines, `plugin-scope` 35→17 lines (removed dangling `ADR-X7` reference).
- Verified: built wheel + sdist contain zero private-identifier leaks; full test suite green (2404 passed, 88.69% coverage).

### Added
- Markdown-memory source (`memory-markdown-source-v1`): product memory is now `.md` atoms with YAML frontmatter; panel renders via `mistune`; deleted renderer/schemas/HTML templates from the old YAML/HTML memory approach.
- Panel Kanban tab: task-state board (`[ ]`/`[-]`/`[x]`) with `/api/kanban` endpoint; handoff verdict gate enforced at panel level (`panel-kanban-v1`).
- Spec-context tree-v2: `ALIVE`/`DEAD` context states, new verbs (`bind`/`unbind`), per-release session locks with `acquire`/`release` semantics (`spec-context-tree-v2`).
- Per-release TOCTOU-hardened session locks: `Impl-XOR-Review` lock enforcement with stale-lock detection and temp-race fixes (`r2-lock-toctou-hardening-v1`).
- `ctx-inject v2`: `context use` → `bind` rename; `primary_context.json` retired from hook; `ctx-inject.sh` updated to v2 context resolution.
- `dadaia public stage` sanitization: defaults for new workspaces scrubbed of private agentic config.

### Changed
- `specs/` carved out of the public repository: marked untracked + added to `.gitignore`; private infra paths and project slugs that had leaked via the specs tree are now excluded from the wheel and sdist.
- `public/data/AGENTS.md` language default is now language-neutral (was "Portuguese (BR) by default").
- GitHub Actions SHA pins corrected: malformed `actions/download-artifact` SHA in `release.yml` fixed; all action pins refreshed.

### Fixed
- `release.yml`: corrected malformed `actions/download-artifact` SHA pin that broke the trusted-publishing release job.

### Removed
- Two private academy modules removed from the `dadaia_workspace/` package tree (private infra docs; 12 files).

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
