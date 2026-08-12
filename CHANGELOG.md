# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — spec release v0.5.0

Lands in the same unreleased `0.5.0` package version as spec release v0.3.0 below.

### Removed
- **The four competing context-resolution ladders and the bind-epoch marker
  subsystem.** `core.specs_resolver.resolve_context()` is now the single authority
  implementing the `DADAIA.md` §3 rung law verbatim (rung 0 caller input / explicit write
  target, rung 1 `DADAIA_CONTEXT`, rung 2 this session's own live record keyed by the
  harness-native session id, rung 3 the repo containing the cwd). The CLI seam, the SDD
  gate, `container` and the ctx-inject hook all consume it. Deleted with the ladders: all
  three marker-attribution algorithms, the `session_identity` marker writers/readers,
  `sdd_post_gate._adopt_attributed_bind`, `.dadaia/states/bind_epoch/`, and
  `cli._specs_resolution.current_ancestry_pids` — 132 occurrences across 18 files → 0.
  `core/specs_resolver.py` went 369 → 202 lines; the production package is net −194 lines
  across the release.
- The `DADAIA_SESSION_ID` **resolution** channel (it survives only as a session identity
  for the CLI/hook heartbeat), the dead `DADAIA_AGENT_RUNTIME` alias (zero writers), the
  hardcoded self-hosting-slug rung, the env pop/restore workaround, and the `cwd/specs`
  fallback in `resolve_specs_dir`. Resolution now reads one environment variable:
  `DADAIA_CONTEXT`.

### Changed
- **Context-memory injection triggers on the session record's `bound_at`** instead of a
  marker mtime. One intended behavior difference: a **same-context re-bind now
  re-injects**, so a mode or release change reaches a live session.
- **Kimi Code binds through `DADAIA_CONTEXT` exported at harness launch** (rung 1) — the
  harness exposes no session-id environment variable. `dadaia context bind` now prints a
  loud warning when it can neither key a harness-native record nor see `DADAIA_CONTEXT`,
  so a binding can never become a silent no-op.
- `DADAIA.md` §3 amended for precision and re-projected; the skills and
  `CONSUMER_VALIDATION_RECIPE.md` teach the three rungs, the plain-shell path and the kimi
  launch-env profile.
- The import-linter contract `bind-resolution-seam-is-a-single-home` rewritten for the new
  seam: exactly three sanctioned direct importers (`cli._specs_resolution`, `container`,
  `hooks`), still zero `ignore_imports`. Hooks import the authority directly by law — no
  hook imports `container`, pinned by a new attesting import-surface test (hook write-path
  latency 2.25 s → 0.46 s).

### Fixed
- **`dadaia specs doctor` is satisfiable again.** A bug-ledger coherence violation is now
  reported only while no later compensating `reported` event exists for the same `bug_id` —
  the append-only store's own vocabulary heals its history, while per-event enforcement is
  unchanged and a fresh uncompensated violation still ERRORs. Two legal appends healed the
  one historical row; the doctor exits 0 on the self-hosting context for the first time.
- Install-ledger relpaths are validated in `LedgerEntry.__post_init__` — empty, absolute,
  `..`-bearing, backslashed and non-normalized POSIX forms are rejected at the one
  construction authority, covering both the prune loop and the foreign-projection scan
  (CWE-22 class).
- `DoctorLine.render()` escapes control characters, so no producer can forge a second
  physical doctor line (CWE-117).
- The `entities-derivation` verifier emits a typed `ENT-DERIVE-1` error line for
  malformed-but-valid JSON shapes instead of letting `AttributeError`/`TypeError` escape.
- The kimi telemetry reader contains `sessionDir` lexically against the index parent before
  `stat`, degrading through its existing `OSError` branch; ships with the reader's first
  test file.
- A new `remove_legacy_bind_epoch_state` install migration sweeps orphan
  `.dadaia/states/bind_epoch/` markers left by earlier releases (retained one release).

## [0.5.0] — Unreleased (spec release v0.3.0)

### Removed
- **Removed the dadaia-workflows engine entirely.** The four `dadaia lifecycle`
  Python workflows (backlog-definition, release-definition, implementation-reviews,
  audit), the Layer-2 worker runtimes (codex/pi/claude-sdk/fake adapters,
  headless adapter base), workflow model policy + profiles, lifecycle fragments and
  personas assets, the lifecycle run store, workflow handoff models/doctors, the
  panel Workflows and Model-policy tabs, the `dadaia reports workflow-*` verbs, the
  certification `workflow-*` checks, `features/ai_surface`, and every related test
  (~52k LOC total). The SDD flow (Arm A) is now agent-dispatched and
  document-governed — SPEC/PLAN/TASKS + ACTIVE.md + the deterministic gate and git
  chokepoints are unchanged. Rationale: the bug-ledger audit measured 200/416 bugs
  (48%) in this subsystem with a 96% additive-fix ratio and 0.48-day median
  family recurrence; deleted surface goes quiet, patched surface does not.
- `dadaia-capabilities-v1` schema replaced by **`dadaia-capabilities-v2`** (breaking):
  the required `workflows` key and the certification `deterministic_fake_workflows` /
  `live_harness_canaries_required_for_release` constants are gone.

### Changed
- **`public_assets` install de-flagged**: `install()` now resolves its arguments once
  into an immutable `InstallPlan` and runs an ordered, flag-free step pipeline
  (`OverwritePolicy` replaces `force: bool` internally; `scope`/`only` select steps).
  Public port signatures and install output are byte-identical.

## [0.1.24] — Unreleased

### Removed
- **Removed OpenCode support entirely (both agentic layers).** The OpenCode entry
  harness, the `OPENCODE_RUN` Layer-2 worker kind and its adapter, the `.opencode/`
  projection target, `opencode.json`, the OpenCode gate plugin, and all OpenCode
  references across code, tests, docs, and the AI surface are gone. The supported
  harness set is now exactly **Claude Code, Codex, and PI**.

## [0.1.7] — 2026-06-13

Consolidated release: the single published version after `0.1.5`. It folds in all
work from the never-tagged `0.1.6`–`0.1.10` development line — cross-platform
support, the process-execution layering law, spec/memory fidelity, the full
workspace-audit remediation, and panel/scaffolder/git security hardening — shipped
under one version through the release-candidate gate rather than as a string of
per-fix releases.

### Added
- **Cross-platform support (Linux / macOS / Windows).** `core/platform.py`
  platform-detection seam (sole `sys.platform` call site) + a port/adapter boundary
  for OS-sensitive domains: file locks (fcntl / msvcrt), telemetry refresh lock, file
  permissions (chmod / `icacls`), process probe, and signals/shutdown. New
  `dadaia_workspace/hooks/` Python governance package replaces the bash hooks so SDD
  governance is enforced on stock Windows (no Git Bash required). 3-tier resilience
  contract (fail-loud security / degrade-with-log / unsupported-at-construction).
  `import-linter` contracts enforce the layering law in CI.
- Phased 3-OS CI matrix: an importability-smoke job (Windows + macOS) plus
  Windows/macOS unit and contract legs (Ubuntu remains the hard gate).

### Changed
- **Model strategy unified on the registry single source** (`core/model_registry`):
  `MODEL_MAP` / `PRICING_TABLE` are derived views; public doctor validates agent
  `model:` frontmatter + key-set sync. Deep-tier personas (product-engineer,
  qa-engineer, ai-engineer, software-architect, project-auditor) and the
  dispatch-tier personas (software-engineer, security-reviewer, code-reviewer) all
  run `claude-opus-4-8`.
- Process-execution layering law completed: `features/` modules no longer import
  `subprocess` directly. New `ProcessRunner` Protocol
  (`core/protocols/process_runner.py`) with production adapter
  (`infrastructure/subprocess_runner.py`), consumed via DI by `import_`,
  `ci_preflight`, `specs/doctor`, and `server_registry`; `import-linter` contract
  `features-no-subprocess` enforces it. `container.py` platform branching reads the
  `PLATFORM` capability singleton.
- Bash hook quartet retired; Python hooks are the sole gate surface (PreToolUse
  scoped to write tools; Bash-tool writes documented out of the determinism envelope
  with doctor backstops).
- AI surface (AGENTS.md, rules, skills, personas) rewritten to describe real
  enforcement vs discipline (14 contradictions fixed); memory + constitution §8
  rewritten to the merged kernel. Agent persona parity pass: `[SCOPE ERROR]` redirect
  block in all 9 core personas; report-emission prose deduplicated to
  `workspace-protocol §4`; vestigial `opencode_model` frontmatter keys removed.
- `Operating System :: OS Independent` classifier corrected to
  `Operating System :: POSIX :: Linux` until the 3-OS CI matrix graduates to a hard
  gate.
- All text I/O specifies `encoding="utf-8"` (Windows cp1252 corruption fix); JSON
  stores route through a single `_atomic_write_text` chokepoint using `os.replace`.
  venv executable paths resolved via the platform seam (`Scripts/python.exe` on
  Windows).
- Test architecture: harness-env fixture contract (hook behavior tests run as real
  subprocesses; `DADAIA_*` setenv + hook-import ratchets at zero baseline), two-actor
  concurrency e2e asserting on lock-file history, drift-ratifying tests killed,
  consistency-contract + lifecycle-asymmetry policies.

### Fixed
- SDD gate classifier re-rooted context-relatively: ADDITIVE/MEMORY/FROZEN classes
  now live inside `repos/<slug>/` (unmatched in-repo ⇒ MUTATING, never UNGATED);
  symlinks canonicalized before classification. Kills the
  lease-theft-by-additive-write CRITICAL.
- Lease liveness = TTL + PID veto: holder records a long-lived harness pid
  (payload/getppid); TTL-stale + alive ⇒ yield (no takeover), dead ⇒ takeover; renew
  runs inside the same O_EXCL CAS (race fixed); heartbeat renews on every PostToolUse
  from the harness-native session id (Claude `*` matcher, Codex match-all).
- Session identity consolidated into a single owner module (`session_identity`); bind
  `--mode` optional (default read), persisted in the session record + context
  incumbent pointer; gate mode resolution env → record → live-incumbent →
  IMPLEMENTATION; READ binds are non-acquiring.
- `dadaia ci preflight` no longer self-pollutes (ruff `--no-cache`, mypy cache
  redirected, pollution guard = session snapshot diff) — the pre-push gate passes
  end-to-end; pre-push hook probes the workspace venv (`$DADAIA_BIN` → walk-up →
  poetry → repo venv, fail-closed).
- specs doctor ledger invariants (SPEC-DOC-024..029): phase↔markers,
  CLOSURE-before-archive, unique release ids, naming canon, constitution ref
  resolution, lease↔session coherence.
- Spec/memory fidelity: all 34 confirmed findings of the drift audit resolved —
  memory atoms document the real doctor check codes, the Python-hook SDD gate, the
  hard-gated 3-OS CI matrix, the full CLI/protocol inventory, and a roster without the
  phantom `researcher` agent.
- The CLI is now importable on Windows: the unconditional top-level `import fcntl` in
  the locking and telemetry modules (which crashed every `dadaia` invocation at
  import) is removed and delegated to platform adapters.
- Windows security no-ops closed: the panel auth token is owner-only via `icacls` or
  the panel refuses to start (CWE-732); `/proc` scans and `os.getuid` degrade safely
  off-Linux.

### Security
- Panel HTTP handler: enforce Bearer auth on workspace-sensitive routes that were
  previously served by the unauthenticated dispatch loop — `/reports/<path>`,
  `/api/panel-status`, `/api/contexts`, `/memory/<slug>/<path>`,
  `/memory-view/<slug>/<path>` — whenever the panel is NOT loopback-bound (defense in
  depth; loopback keeps the zero-friction local default). (F-01/F-02/F-04)
- Scaffolder renders templates with a Jinja2 `SandboxedEnvironment`, blocking template
  access to Python internals. (F-03)
- `GitSubprocessClient.clone` refuses unsafe URLs (`ext::` transport and
  option-injection via a leading `-`) before invoking git. (F-05)
- Panel loopback auth bypass removed (tokenless sensitive API ⇒ 401 even on
  127.0.0.1; tokenized-URL handoff, token file modes re-tightened to 0o600).
- `context dead` refuses untracked files without `--commit`; `--commit` runs a
  structural secret scan (incl. cert/key file suffixes) before any push.
- public-privacy gate fails closed: packaged baseline structural denylist scans even
  without an operator denylist.

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
