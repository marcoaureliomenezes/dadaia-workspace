---
slug: tech-stack
title: Tech Stack Memory
category: core
tldr: Approved toolchain, runtimes, approved deps, and canonical commands for dadaia-workspace.
summary: Catalogs approved Python/Node runtimes, core dependencies, formatting/lint
  tools, agent runtimes, and canonical CLI commands. Injected at every session start.
tags:
- tech-stack
- dependencies
- toolchain
- constraints
token_estimate: 2325
last_updated: '2026-07-03'
release_origin: v0.1.53
---

## Languages

Language| Version| Use
---|---|---
Python| ^3.12| Entire CLI, features, infrastructure, container, pytest tests.
Bash| 4+ POSIX-compatible| Shell assets in the product: only the git chokepoints `pre-commit-lease-gate.sh` + `pre-push-ci-gate.sh` (git hooks, deliberately shell; git-for-Windows ships bash) — all harness governance hooks are the Python package `dadaia_workspace/hooks/` (context-injection mechanics: [[context-management]]).
HTML5 + Mermaid| `mermaid` fences in Markdown| Reports in `.dadaia/reports/<ctx>/<agent>/*.html`; memory atoms are `.md` rendered in-memory. The panel does NOT load Mermaid from a CDN (CSP `script-src 'self'`): fences become `<pre class="mermaid">` displayed as source
Markdown| CommonMark| Atomic memory atoms in `specs/memory/*.md` (frontmatter `memory-frontmatter-v1` + Markdown body); SPEC/PLAN/TASKS/CLOSURE, constitution, backlog, skill/agent definitions
YAML frontmatter| YAML 1.2| Frontmatter of agents/skills/workflows and memory atoms (`memory-frontmatter-v1`: `additionalProperties: false`)
JSON| stdlib| Runtime state in `.dadaia/states/`, `manifest.json`; `specs/memory/product/catalog.json` (generated from `.md` frontmatter, committed, machine-readable feature index)

## Runtimes and tools

Tool| Version| Role
---|---|---
Poetry| core (build-backend)| Build, lock, virtualenv via `.venv` or poetry-managed env
pytest| >=8,<10| Test runner — test taxonomy and gates owned by [[quality-assurance]]
pytest-cov| >=5,<8| Coverage measurement
ruff| >=0.15| Linter + formatter (line-length 100, target py312)
mypy| >=1.10,<3.0| Type checker
git| 2.x| VCS; `git_subprocess.py` wraps commands

## Agent runtimes

**This section is the ONLY source of the harness/runtime roster** (constitution §0,
roster invariant; SPEC-DOC-037 prevents the constitution from enumerating it). The roster:

  * **Layer 1 — entry harnesses (what the operator launches in the terminal):** exactly **`{claude, codex, pi}`**.
  * **Layer 2 — workflow worker harnesses (selectable in `dadaia lifecycle`):** exactly **`{pi, codex}`** (+ **`fake`** test-only). `claude` is rejected as a workflow `--harness` — **Claude Code is Layer-1-only by law** (cost bound).
  * **`AgentRuntimeKind` (`core/models/lifecycle.py`) — 4 members:** `FAKE`, `CODEX_EXEC`, `CLAUDE_SDK`, `PI_HEADLESS`. `CLAUDE_SDK` is kept importable + unit-tested but is **not selectable** as a workflow harness.

Per harness (per-runtime truth in `specs/memory/product/harness/` — [[harness-claude-code]], [[harness-codex]], [[harness-pi]]):

  * **Claude (Anthropic)**: native Layer-1 runtime; agents projected verbatim to `.claude/agents/` via `dadaia public install --target claude`. The `ClaudeSdkAdapter` (`infrastructure/claude_sdk_runtime.py`) remains behind `AgentRuntimePort`; it depends on the **optional** `claude-agent-sdk` extra (optional extra `claude-sdk` in `pyproject.toml`/`poetry.lock` — lazy-imported, not a base dependency, never installed by default; offline-first build preserved; absence ⇒ FAILED result with an actionable `pip install claude-agent-sdk`).
  * **Codex (OpenAI)**: Layer 1 (TUI) and Layer 2 (`CODEX_EXEC` via `codex exec`). Doctor checks D-CX-1..8. 12 TOML agents in `.codex/agents/` (9 core + 3 plugin stubs) with registry-derived tiering — tier-view mechanics, the D-CX-4 lint, and the live-verification harness are owned by [[harness-codex]]. Zero `claude-*`/Opus/Sonnet/Haiku leaks. Command policy `.codex/rules/*.rules` in `prefix_rule(...)` with venv-form paths. **Hooks run only in interactive sessions** — headless `codex exec` fires no hooks ([[harness-codex]]). Workflows in `.codex/workflows/` (reference-only). Layer-2 models: `(gpt-5.5,high)` / `(gpt-5.5,medium)`.
  * **PI (`@earendil-works/pi-coding-agent`)**: Layer 1 (entry harness) **and** Layer 2 (`PI_HEADLESS`), selectable per step via `--harness pi` / `--step-harness x=pi`. The `PiHeadlessAdapter` (`infrastructure/pi_runtime.py`) drives a PI worker via `pi --mode json` (subprocess, injectable runner, no PI client at module load). PI is an **OPTIONAL external CLI runtime installed by the operator**, invoked as an external binary — **NEVER** a locked/pinned dependency: it is not a Python dependency at all (absent from the lockfile), it is not imported in build/test, and the build stays offline-first without it. **Auth: PI runs under the operator's Codex subscription via `~/.pi/agent/auth.json`** (provider openai-codex) — no Anthropic key is required. **Layer-2 models (4):** `(gpt-5.5,high)` / `(gpt-5.5,low)` / `(gpt-5.3-codex,medium)` / **`kimi-2.7:high`** — the curated OpenRouter id via `LAYER2_EXTRA_MODEL_IDS` (`core/harness_models.py`), selectable through the built-in profile `pi-openrouter-kimi-high`; `kimi-*` ids have no pricing row in the registry (cost `None`, never fabricated). The `pi --mode json` event-stream schema is verified by the opt-in tests `DADAIA_PI_LIVE=1` / `DADAIA_E2E_REAL_WORKER=1` (`tests/integration/pi_live/`, **not** CI-gated). Live-verified build: `pi` **0.79.3**. **PI telemetry:** `features/telemetry/reader/pi.py` ingests **metadata only** from `~/.pi/agent/sessions/` (invariant T1 — no body/content; cost never faked); degrades idle on IO/parse failure.
  * **CLI versions:** `pi` 0.79.3 live-verified; the verified `codex` version has not been captured yet (do not invent).



## Model assignments (9 core agents + 3 plugin stubs)

**Single tier in practice:** the **9 core agents** run on `claude-opus-4-8` — there
is no tier-split in production (verifiable: all 9 frontmatter `model:` values resolve
to `claude-opus-4-8`). Per-dispatch override via `DADAIA_MODEL_OVERRIDE` when the
dispatcher's policy justifies it. Optional packs may define their own agents and
models outside the public default.

**Single source:** `dadaia_workspace/core/model_registry.py` is the only source of
model ids/pricing/tier (`ModelEntry{claude_id, codex_id, pricing dated
append-only, tier}`); `MODEL_MAP` (runtime transforms) and `PRICING_TABLE`
(telemetry) are derived views, with a key-equality contract test. `dadaia
public doctor` fails on a `model:` frontmatter that does not resolve in the registry.

**Reserved entry (used by no agent):** the registry still defines
`claude-fable-5` with `tier="deep"` (and the Codex mapping `deep→high`), but **zero
core agents resolve to it** — all 9 are `dispatch`-tier opus-4-8.
`claude-fable-5` is region-restricted; the operator rule is **NEVER** pin an
agent to Fable-5. The entry remains a reserved registry definition, not a live
assignment.

Agent| Model| Note
---|---|---
project-manager| `claude-opus-4-8`| Dispatcher / lease coordinator
project-auditor| `claude-opus-4-8`| Dispatcher / audit fan-out
product-engineer| `claude-opus-4-8`| Curator / memory guardian
software-engineer| `claude-opus-4-8`| Implementation leaf (absorbs python/node/backend)
ai-engineer| `claude-opus-4-8`| AI-entity surface owner (harness-mastery synthesis workload)
software-architect| `claude-opus-4-8`| Architectural review leaf (ADDITIVE)
qa-engineer| `claude-opus-4-8`| Review → commit gate leaf
security-reviewer| `claude-opus-4-8`| Review → push gate leaf
code-reviewer| `claude-opus-4-8`| Review → PR gate leaf
frontend-engineer (plugin)| — (no `model:` frontmatter)| Plugin stub (frontend-design pack); no behavior and no model assignment until the pack ships
design-specialist (plugin)| — (no `model:` frontmatter)| Plugin stub (frontend-design pack); no behavior and no model assignment until the pack ships
devops-engineer (plugin)| — (no `model:` frontmatter)| Plugin stub (devops pack); no behavior and no model assignment until the pack ships

## Plugin inventory

Plugin| Status| Scope
---|---|---
`playwright`| Retained| Universal — used by `qa-engineer` (E2E) and `frontend-engineer`; optional packs may widen usage.
`frontend-design`| Not yet distributed| Plugin pack for `frontend-engineer` + `design-specialist` (the `devops` pack covers `devops-engineer`). No install command exists yet — tracked by backlog `plugin-packs-and-install-command`. Until it ships, core agents handed a plugin-domain task respond `[PLUGIN REQUIRED]` and route to the operator, per `dadaia_workspace/public/rules/plugin-scope.md`.
`superpowers`| Removed| Uninstalled in P1; native replacements via Tier-A skills.
`skill-creator`| Removed| Uninstalled in P1; skill authoring is `ai-engineer`'s responsibility, editing `dadaia_workspace/public/skills/` directly.
`code-simplifier`| Removed| Uninstalled in P1; refactoring stays with `software-architect` + implementers.

## Schema handoff-v1.1

The JSON sidecar contract between agents is versioned in
`dadaia_workspace/public/schemas/handoff-v1.schema.json`; current version **v1.1**.
Field-level contract, validation CLI, and emission defaults: [[agent-comms]].

## Approved dependencies

Dependency| Version| Layer| Justification
---|---|---|---
typer| >=0.25 (extras=[all])| cli/| CLI framework with auto-completion and rich formatting
rich| >=13,<16| cli/| Pretty terminal output
openpyxl| ^3.1| infrastructure/| Excel spreadsheet reading (academy)
pyyaml| ^6.0| infrastructure/ + features/| YAML frontmatter parsing (memory atoms, agents/skills/workflows); `yaml.safe_load` used by lint and catalog scripts
jsonschema| ^4| features/specs/| JSON Schema validation; now used for `memory-frontmatter-v1.schema.json` validation in `lint-memory-atoms.py`. The per-atom YAML schemas (memory-structured-source-v1) were deleted; `jsonschema` remains for frontmatter validation.
mistune| >=3.0,<4.0| features/panel/views/| Markdown → HTML render in-memory for the memory viewer (D-1, memory-markdown-source-v1). Pure-Python, zero transitive deps. Custom hooks: mermaid fence, `wikilink`, sanitiser.
types-PyYAML| >=6| dev| Type stubs for mypy
pytest-randomly| ^4.1.0| dev| Random test order per run — flushes inter-test order dependencies
hypothesis| >=6.100| dev| Property-based testing (database redirected outside the repo — repo-hygiene)
jinja2| ^3.1| features/specs/| **Direct** runtime dependency: `features/specs/scaffolder.py` renders the SDD scaffold templates via `SandboxedEnvironment`. NOT used for memory rendering (memory atoms are `.md` rendered by mistune).
import-linter| >=2.11| dev| Layer contracts in `setup.cfg` — full enforcement-status statement single-sourced in [[architecture]] §Enforcement.

**Workspace tooling pins (not project deps):** `poetry` ≥ 2.3.4 and
`dulwich` ≥ 1.2.5 in the operating environments (CVEs named in a comment in
`pyproject.toml`); they do not enter `poetry.lock` — the build-backend is `poetry-core`.

Where each dependency lives, and the import bans the `import-linter` contracts
describe (hexagonal layers — arrow = allowed import direction; enforcement
status: [[architecture]]):

```mermaid
graph TD
  CLI["cli/<br/>typer · rich"]
  FEAT["features/<br/>pyyaml · jsonschema · jinja2 · mistune"]
  INFRA["infrastructure/<br/>openpyxl · pyyaml · git_subprocess · harness adapters"]
  CORE["core/<br/>stdlib only<br/>model_registry · scope_match · models · protocols"]
  CLI --> FEAT
  CLI --> INFRA
  FEAT --> CORE
  INFRA --> CORE
  FEAT -. "BANNED (contract): features ✗→ infrastructure" .-> INFRA
  CORE -. "BANNED: core ✗→ os/subprocess/fcntl" .-> OSP["OS primitives"]
```

`features/` talks to the external world only through `core/protocols/*`, implemented in
`infrastructure/` and injected in `container.py` (hexagonal port/adapter). `core/` is
pure: zero I/O, zero OS primitives — which is why it is testable and cross-platform.

## Restrictions and prohibitions

  * DO NOT add dependencies outside this list without an approved release justifying it.
  * DO NOT use libs with network access in build/test (offline-first).
  * `claude-agent-sdk` is an **optional extra** (`claude-sdk`, `pyproject.toml`), NOT a base dependency: it appears in `poetry.lock` as `optional = true`, is never installed by default, is not imported at module-load, and is lazy-imported only by the `ClaudeSdkAdapter` when the operator chooses to run a step on the Claude SDK harness. Build and tests stay offline-first without it.
  * `pi` is an optional external CLI runtime installed by the operator — never a locked Python dependency. Runtime/auth facts stated once in `#Agent runtimes`.
  * DO NOT use threading/multiprocessing in features — any process-level concurrency runs through the lifecycle engine's bounded worker subprocesses (injected `ProcessRunner`), never spawned inside a feature.
  * DO NOT call `os.system`/`subprocess` outside `infrastructure/` — features use protocols.
  * DO NOT import Python <3.12 backports — minimum runtime is 3.12 (match/case, native generic types, type statement).
  * DO NOT write into `.claude/`, `.codex/`, `.pi/`, `.agents/` directly — only via `dadaia public install` from `public/`.



## Canonical commands

How to run, test, lint, and package:


    # Setup
    poetry install

    # Run CLI (dev)
    poetry run dadaia <subcommand>
    # or globally after install
    dadaia <subcommand>

    # Tests
    pytest                                  # all
    pytest tests/unit/features/specs/       # specs doctor unit tests
    pytest -k test_clean_tree               # by name

    # Lint + format
    ruff check .
    ruff format .

    # Type check
    mypy dadaia_workspace

    # Asset chain
    dadaia public stage
    dadaia public install --target all      # plain install propagates updates (overwrites on hash mismatch); --force only to clobber a hand-edited (locally-diverged) projection
    dadaia public doctor

    # SDD
    dadaia specs doctor                     # SDD structure
    dadaia specs doctor --json              # machine-readable

    # Backlog-consistency engine (features/backlog/, v0.1.25)
    dadaia backlog subjects                 # lists the live canonical anchor set (optional --kind / --resolve "<ref>")
    dadaia backlog doctor                   # BL-SCHEMA/DUP/CONFLICT/STALE; exit !=0 on violation (wired into pre-commit + CI)
    dadaia backlog doctor --explain         # shows how a proposed subject resolves (anchor | UNRESOLVED | AMBIGUOUS)

    # backlog_definition dadaia-workflow (features/lifecycle/workflows/backlog_definition.py, v0.1.26)
    dadaia lifecycle backlog define --harness {pi|codex|fake} --model <id>   # workflow §4 ORIENTED; Python-owned gates; LAW 1/LAW 2 (claude rejected)
