# dadaia-workspace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/dadaia-workspace)](https://pypi.org/project/dadaia-workspace/)

**AI-native workspace management for multi-agent, Spec-Driven Development.**

`dadaia-workspace` gives AI coding agents a structured, governed shared workspace:
scoped project contexts, a Spec-Driven Development (SDD) flow with deterministic
gates, a persona-based agent roster with installable **plugin packs**, canonical
agentic-asset projection across **four** AI harnesses, and a real-time monitoring
panel.

It supports, as peer entry harnesses: **Claude Code, Codex, PI (`pi-coding-agent`),
and Kimi Code (the `kimi` CLI)**, plus a **consumer-side validation agent** as the
release gate. There is no separate workflow-engine layer — the ordered SDD flow is
agent-dispatched, carried out by dispatching the owning agent for each stage against
the SDD documents, inside whichever entry harness is running. It is designed to be
operated by **humans and by agents**: every capability is reachable through a
discoverable CLI, and every state surface has a machine-readable form.

Open source under the MIT license. Source, issues, and contributions:
[github.com/marcoaureliomenezes/dadaia-workspace](https://github.com/marcoaureliomenezes/dadaia-workspace).

---

## Install

```bash
pip install dadaia-workspace
```

Requires Python 3.12+.

---

## Quick start

```bash
dadaia init                        # bootstrap .dadaia/ + project agent assets (.claude/, .codex/, .pi/, .kimi-code/)
dadaia init --harness claude,pi    # or scaffold only a subset of harnesses (harness profile)
dadaia doctor                      # health check: contexts, assets, gates, presence
dadaia panel                       # local dashboard (http://localhost:4999)
```

From there, agents self-discover the rest via `dadaia --help`. Every command group
supports `--help` at every level.

---

## The entry harnesses

There is no separate workflow-engine layer. Every agent — whether the operator's own
entry session or a dispatched sub-agent — runs inside one of the four supported entry
harnesses, and the ordered SDD flow (backlog definition → release definition →
implementation with its reviews → audit) is carried out by dispatching the owning
agent for each stage against the SDD documents (`ACTIVE.md`, SPEC, PLAN, TASKS,
CLOSURE) — never by a procedural engine.

```mermaid
flowchart TB
    OP(["Operator in the terminal"])
    subgraph L1["Entry harness (what you launch)"]
        direction LR
        CC["claude"]:::h
        CX["codex"]:::h
        PI["pi"]:::h
        KC["kimi"]:::h
    end
    GOV["Governance: AGENTS.md read up-tree natively<br/>+ projected .claude/ .codex/ .pi/ .kimi-code/<br/>+ PreToolUse gate (where supported) + git chokepoints"]
    DISPATCH["Agent-dispatched SDD flow<br/>(owning agent per stage, against SPEC/PLAN/TASKS)"]
    OP --> L1 --> GOV --> DISPATCH
    DISPATCH -->|"git-diff write boundary + git chokepoints"| OUT(["production: code · specs · memory"])
    classDef h fill:#1f6feb,color:#fff,stroke:#1f6feb;
```

- **The entry harness (the CLI you launch).** The AI coding agent a human launches
  in the terminal: **Claude Code, Codex, PI (`pi-coding-agent`), or Kimi Code** (the
  `kimi` CLI). It is governed by the workspace-root `AGENTS.md` (read natively up the
  directory tree) plus the projected per-runtime asset trees (`.claude/`, `.codex/`,
  `.pi/`, `.kimi-code/`) and the deterministic gate wiring each harness gets (hooks,
  rules, skills, sub-agents where the harness supports them). **All four are
  supported entry harnesses.**
- Headless codex/pi sessions (e.g. a dispatched sub-agent) remain bounded by the same
  **git chokepoints** as any other session — pre-commit presence warning and the
  pre-push security-verdict gate — regardless of which harness is running.

---

## Supported harnesses

| Harness | Entry harness support |
|---|---|
| **Claude Code** | ✅ `.claude/` + PreToolUse hook + git chokepoints |
| **Codex** | ✅ `.codex/` (hooks fire in the interactive TUI; headless `codex exec` is chokepoints-only) |
| **PI** (`pi-coding-agent`) | ✅ `.pi/` (no PreToolUse hook → chokepoints-only) |
| **Kimi Code** (`kimi` CLI) | ✅ `.kimi-code/` + PreToolUse/PostCompact hooks via a managed block in `~/.kimi-code/config.toml` (Kimi Code has no project-level config file) |

## Consumer validation — the release gate

A **consumer-side validation agent** running the shipped recipe on a real
workspace is the release gate of dadaia-workspace: it certifies every candidate
wheel before deploy, and no version is published without its `CERTIFIED_100`
verdict. A consumer environment is declared **supported** only when its
day-to-day activities run on dadaia-workspace without product bugs, proven (not
assumed):

- The shipped consumer validation recipe
  (`dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md`) carries a
  **Real-use matrix (R-01…R-08)** built from a real consumer's day-to-day
  inventory: the live Codex chain with per-link artifact proofs, canonical
  backlog consumption, fresh/old-context doctor-clean repair, terminal-state
  honesty, bug-ledger round-trip, fake-chain honesty, and the Kimi Code harness
  surface.
- The deterministic certification (structural + F-01…F-26) is necessary but
  **never sufficient alone** — a candidate is green only when the full real-use
  round reports zero failures.
- The consumer's own bug stream must converge to **zero open bugs** (product fixes
  land by root-cause class; environment and wrong-usage findings are classified,
  never patched over).

**Harness profiles.** `dadaia init --harness <set>` scaffolds only the harnesses you
use (persisted in `.dadaia/states/harness_profile.json`). `dadaia public install` and
`dadaia public doctor` are **profile-aware**: a claude-only workspace projects and
doctors only `.claude/`, and out-of-profile assets found on disk are surfaced, never
silently ignored. With no profile, all harnesses are targeted (back-compatible).

All projections are generated from one canonical source at `dadaia_workspace/public/`
via `dadaia public stage && dadaia public install`. The Claude SDK and PI runtimes are
**optional, operator-installed** externals — the build stays offline-first without them.

---

## Spec Context Project

A **Spec Context Project** is the keystone unit: *one canonical `specs/` folder bound
to one git repository*, following the SDD lifecycle. Binding a session to a context
triggers a value chain: **bind → inject** (the context's `constitution.md` + memory) **→
enforce** (no production change without an approved release + reserved task) **→
parallel** (each context carries exactly one MUTATING lease, so multiple contexts can
be worked concurrently and safely).

```bash
dadaia context list              # all Spec Context Projects
dadaia context show --json       # active context (machine-readable; agent use)
dadaia context bind <name>       # bind the session (selects injected memory; refreshes incumbent)
```

---

## Agent roster & personas

The workspace ships a **9-agent core roster** plus **3 plugin agents** (enabled by
installing their pack — see the next section). Each agent is projected into every
harness in the profile; `project-manager` is the Layer-1 coordinator.

| Core agent | Role |
|---|---|
| `project-manager` | Layer-1 coordinator: dispatch, release governance, backlog curation |
| `product-engineer` | Spec author + memory guardian (SPEC/PLAN/TASKS/CLOSURE, `specs/memory/`) |
| `software-engineer` | Generic implementer (TDD-first, conventional commits) |
| `software-architect` | Anti-slop architecture reviews, root-cause gates |
| `qa-engineer` | Test pyramid, E2E ownership, commit-gate reviews |
| `security-reviewer` | Vulnerability audits; the mechanical **push gate** verdict |
| `code-reviewer` | PR/branch six-axis reviews |
| `project-auditor` | Spec/memory-vs-code drift audits, scorecards |
| `ai-engineer` | Exclusive owner of agents/skills/rules/workflows; context engineering |

| Plugin agent | Domain | Pack |
|---|---|---|
| `frontend-engineer` | Browser HTML/CSS/JS/TS/React | `frontend-design` |
| `design-specialist` | UX/UI, design specs, visual review | `frontend-design` |
| `devops-engineer` | CI/CD, GitHub Actions, gitflow, deploy | `devops` |

---

## Plugin packs

Plugin agents ship as inert stubs until their pack is installed:

```bash
dadaia plugin list                       # available packs + install state
dadaia plugin install frontend-design    # enable frontend-engineer + design-specialist
dadaia plugin install devops             # enable devops-engineer
dadaia plugin doctor                     # per-projected-file status of installed packs
```

Packs are distributed **inside the package** (no network fetch): real agent bodies
plus curated skills, projected into the harness profile like any canonical asset.
Installs are recorded in `.dadaia/states/installed_plugins.json`; a later core
`dadaia public install` **preserves installed pack bodies** (it never regresses them
to stubs), and `plugin install` is idempotent.

---

## The SDD flow — agent-dispatched, not engine-run

There is no workflow engine. The ordered SDD flow has exactly **four** stages —
backlog definition, release definition, implementation with its reviews, and audit
— and each is carried out by dispatching the owning agent for that stage (see
"Agents & personas" above) against the SDD documents themselves:

| Stage | Entry agent | Governing document(s) |
|---|---|---|
| Backlog definition | `project-manager` (curates), `product-engineer` (reads to author) | `specs/backlog/**` |
| Release definition | `product-engineer` | SPEC, PLAN, TASKS |
| Implementation + reviews | surface implementer, then the review trio | TASKS, review handoffs |
| Audit | `project-auditor` | `specs/audits/**` |

Durable handoffs from each stage are **registered under the Spec Context**
(`specs/releases/<id>/handoffs/`, backlog work in `specs/backlog/handoffs/`) —
never in an opaque runtime path.

---

## Development lifecycle phases

A release matures through explicit phases; the SDD gate keys off the active phase
(`specs/releases/ACTIVE.md`):

```mermaid
flowchart LR
    D["DEFINITION<br/>SPEC · PLAN · TASKS · memory"] --> I["IMPLEMENTATION<br/>code · tests"]
    I --> R["REVIEWS<br/>QA → commit · security → push · code-review → PR"]
    R --> C["CLOSURE<br/>CLOSURE.md · memory · archive"]
```

- **DEFINITION** — author SPEC/PLAN/TASKS; memory (`specs/memory/`) is writable here.
- **IMPLEMENTATION** — production code + tests; concurrent sessions surface through advisory presence (no locks).
- **REVIEWS** — `qa-engineer` (commit gate), `security-reviewer` (push gate),
  `code-reviewer` (PR gate). Reviews are ADDITIVE evidence; they mature the release.
- **CLOSURE** — write `CLOSURE.md`, update memory truth, archive the release.

---

## The SDD gate

Enforcement has two deterministic halves:

1. **PreToolUse hook** — one merged Python entrypoint (`dadaia_workspace.hooks.pre_gate`)
   reads each file-write tool call once and evaluates, first-block-wins:
   **root-whitelist → venv-guard → SDD gate**. The SDD gate decides by
   **path-class × lease × memory-phase × mode** (a single per-context TTL lease with a
   PID veto coordinates MUTATING writes). ADDITIVE paths — bugs, backlog, audits,
   reports, handoffs — always flow, for any agent, with no lease.
2. **Git chokepoints** (run as git hooks, independent of any harness hook): a
   **pre-commit lease gate** and a **pre-push** gate that runs `dadaia ci preflight`
   (ruff format/check + mypy --strict + import-linter + pytest) *and* requires an
   APPROVED `security-reviewer` verdict keyed to each pushed commit sha.

The gate reads no SDD artifacts — task markers (`[-]`), `Aprovado` status, and
write-allowlists are agent/coordinator **discipline**, not gate mechanism. Hooks and
chokepoints are installed by `dadaia init` / `dadaia public install` /
`dadaia ci install-hook`.

---

## Governance data stores

Everything an agent needs to reason about product state is a validated, queryable
store — not prose:

- **Bugs — event-sourced JSONL.** `dadaia bugs append --event reported ...` appends a
  schema-validated event; a bug's stream later carries one terminal event
  (`resolved`/`superseded`/`deferred`/`rejected`). `dadaia bugs status` lists open
  bugs; `dadaia bugs stats` aggregates. Bugs are never silently dropped.
- **Backlog — typed intents.** Every entry declares `(subject{kind,ref} → change)`
  intents bound against an auto-derived anchor registry; `dadaia backlog doctor`
  fail-closed checks (BL-*) run in pre-commit and CI.
- **Memory — current product truth.** Curated Markdown atoms under `specs/memory/`
  with a generated feature catalog (`dadaia memory catalog generate`). Memory is
  injected on context bind; it is writable only in DEFINITION/CLOSURE phases.
- **Reports & handoffs.** Agent output is a machine-readable handoff JSON
  (`dadaia reports validate <file>`); HTML reports are emitted only for humans.

---

## CLI reference

```
dadaia [COMMAND] --help   # always works at every level
```

| Command group | What it does |
|---|---|
| `dadaia init` | Bootstrap workspace; `--harness` selects the harness profile |
| `dadaia doctor [--fix]` | Diagnose and repair workspace state (contexts, assets, presence) |
| `dadaia context` | Manage Spec Context Projects (list, bind, show, …) |
| `dadaia plugin` | Install and inspect distributed plugin packs |
| `dadaia ci` | Local CI-equivalent preflight gate + git-hook chokepoints |
| `dadaia public` | Stage, install (profile-aware), and doctor agentic assets |
| `dadaia specs` | SDD release-lifecycle structural checks (`specs doctor`) |
| `dadaia bugs` | Event-sourced JSONL bug telemetry (append/status/stats) |
| `dadaia backlog` | Backlog entries + fail-closed consistency doctor |
| `dadaia release` | Release management commands |
| `dadaia memory` | Memory catalog management |
| `dadaia reports` | Validate handoffs; efficiency-audit marker (`mark-efficiency-audit`) |
| `dadaia repos` | Query the known repos catalog |
| `dadaia server` | Dev server port registry |
| `dadaia academy` | Manage Academy courses |
| `dadaia migrate` / `clean` / `export` / `import` | Migrations, cleanup, portable archive |
| `dadaia panel` | Start the local monitoring panel |

### Asset projection pipeline

```bash
dadaia public stage                     # stage canonical assets into .dadaia/agentic/
dadaia public install --target all      # project to the harness profile (or all)
dadaia public install --target pi       # project to one runtime (claude|codex|pi|agents)
dadaia public doctor                    # drift detection: source → staging → projection
```

`public doctor` exits non-zero on drift and reports per-file `[ok]` / `[drift]` /
`[missing]`. Consumer repos' hand-authored root `AGENTS.md` files are provenance-
protected: only files carrying the generated banner are treated as lib-owned; anything
else is reported `[foreign]` and **never overwritten**.

---

## Monitoring panel

```bash
dadaia panel                            # http://localhost:4999
```

The panel is a local, loopback-bound dashboard (Host-header guarded, no auth on
loopback). Tabs: **Projects** (Spec Context Projects with clickable memory chips),
**1º Agentic Layer** (entry-harness sub-agent model/effort policy), **Reports**,
**Academy**, **Servers** (the dev server registry), and **Games** — four playable
canvas games (Snake, Tetris, Pong, Breakout), each built agent-dispatched. It exposes
a no-auth health probe for automated checks:

```
GET http://localhost:4999/health   →   {"status": "ok", "version": "<running version>"}
```

---

## Agent self-discovery protocol

Agents can operate the workspace with no prior knowledge:

```
1.  dadaia --help                    → full command tree
2.  dadaia doctor                    → workspace health (what's wrong, what to fix)
3.  dadaia context show --json       → active Spec Context Project (machine-readable)
4.  dadaia public doctor             → agentic asset projection state
5.  GET http://localhost:4999/health → panel health probe
```

If `dadaia doctor` exits non-zero, run `dadaia doctor --fix` first.

---

## Links

- PyPI: https://pypi.org/project/dadaia-workspace/
- GitHub: https://github.com/marcoaureliomenezes/dadaia-workspace
- Issues: https://github.com/marcoaureliomenezes/dadaia-workspace/issues
