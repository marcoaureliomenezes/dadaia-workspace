# dadaia-workspace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/dadaia-workspace)](https://pypi.org/project/dadaia-workspace/)

**AI-native workspace management for multi-agent development.**

`dadaia-workspace` gives AI agents (Claude Code, Codex, OpenCode) a structured shared workspace with managed contexts, agentic asset projection, a real-time monitoring panel, and Spec-Driven Development enforcement.

`dadaia-workspace` is open source under the MIT license. Source code, issues, and
contributions live at
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
dadaia init        # initialise .dadaia/ and project agentic assets into .claude/
dadaia doctor      # health check: contexts, assets, panel, SDD gate
dadaia panel       # launch the local dashboard at http://localhost:8080
```

That's it. From here, agents self-discover the rest via `dadaia --help`.

---

## CLI reference

```
dadaia [COMMAND] --help   # always works at every level
```

| Command group | What it does |
|---|---|
| `dadaia init` | Bootstrap workspace: creates `.dadaia/`, projects agent assets |
| `dadaia doctor [--fix]` | Diagnose and repair workspace state |
| `dadaia context` | Manage Spec Context Projects (activate, deactivate, promote, switch) |
| `dadaia repos` | Query the known repos catalog |
| `dadaia public` | Stage and install distributed agentic assets across runtimes |
| `dadaia server` | Dev server port registry (register, list, deregister) |
| `dadaia panel` | Start local monitoring panel (http://localhost:8080) |
| `dadaia specs` | SDD release-lifecycle checks and helpers |
| `dadaia reports` | Inspect and validate agent handoff reports |
| `dadaia orchestrate` | Run multi-agent workflows |
| `dadaia academy` | Manage Academy courses |
| `dadaia export / import` | Portable workspace archive |

### Context management

```bash
dadaia context list                  # list all Spec Context Projects
dadaia context activate <name>       # activate a context (clones repo if absent)
dadaia context show                  # show active context
dadaia context show --json           # machine-readable active context (agent use)
dadaia context promote <name>        # set as workspace primary
dadaia context deactivate <name>     # git-sync and remove from disk
dadaia context use <name>            # isolate shell session to a context
```

### Asset pipeline

```bash
dadaia public stage                          # stage assets from package into .dadaia/agentic/
dadaia public install                        # project assets to all AI runtimes
dadaia public install --target claude        # project to Claude Code only
dadaia public install --target codex         # project to Codex only
dadaia public doctor                         # detect drift between source → staging → projection
```

### Dev server registry

```bash
dadaia server register <port> <project> <url>   # register a running dev server
dadaia server list                               # list all registered servers
dadaia server deregister <port>                  # remove from registry
```

---

## Agent self-discovery protocol

Agents can fully discover and operate `dadaia-workspace` with no prior knowledge:

```
1.  dadaia --help                    → full command tree
2.  dadaia doctor                    → workspace health (what's wrong, what to fix)
3.  dadaia context show --json       → active Spec Context Project (machine-readable)
4.  dadaia public doctor             → agentic asset projection state
5.  GET http://localhost:8080/health → panel health probe (returns {"status":"ok","version":"..."})
```

If `dadaia doctor` exits non-zero, run `dadaia doctor --fix` before doing anything else.

---

## What is a Spec Context Project?

A **Spec Context Project** is a scoped workspace unit: a git repo with a `specs/` directory following the SDD (Spec-Driven Development) lifecycle — `SPEC.md → PLAN.md → TASKS.md → CLOSURE.md`. The `dadaia context` commands let you activate, switch, and isolate contexts across projects.

---

## Supported AI runtimes

| Runtime | Projection target |
|---|---|
| Claude Code | `.claude/agents/`, `.claude/rules/`, `.claude/skills/`, `.claude/workflows/` |
| Codex | `.codex/agents/*.toml`, `.codex/rules/`, `.codex/skills/` |
| OpenCode | `.opencode/agents/`, `.opencode/skills/`, `.opencode/workflows/` |
| Generic agents | `.agents/skills/`, `.agents/workflows/` |

All projections are generated from a single canonical source at `dadaia_workspace/public/` via `dadaia public stage && dadaia public install`.

---

## Panel health probe

The panel exposes a public (no auth) health endpoint for agent monitoring:

```
GET http://localhost:8080/health
→ {"status": "ok", "version": "0.1.2"}
```

Use this in automated checks to verify the panel is running before making authenticated API calls.

---

## SDD gate

`dadaia-workspace` ships a pre-tool hook (`sdd-spec-gate.sh`) that enforces Spec-Driven Development: agents cannot edit production files without an active task marker (`[-]`) in `TASKS.md`. The gate is installed automatically by `dadaia init` and `dadaia public install`.

---

## Links

- PyPI: https://pypi.org/project/dadaia-workspace/
- GitHub: https://github.com/marcoaureliomenezes/dadaia-workspace
- Issues: https://github.com/marcoaureliomenezes/dadaia-workspace/issues
