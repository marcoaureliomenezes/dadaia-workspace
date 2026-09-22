# Memory Catalog — dadaia-workspace

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `.agents/skills/dd-spec-navigator/scripts/memory.py catalog generate`; other
> sections of this file are preserved verbatim.

## Feature catalog

### agents

| slug | title | tldr |
|------|-------|------|
| `agent-comms` | agent-comms | The handoff-v1 JSON contract agents emit, its stdlib validator behind `dadaia reports validate`, and ack-on-consume deletion with a one-day TTL. |
| `agent-orchestration` | agent-orchestration | Three dd- personas dispatched by the main thread alone; ordered work carried by the SDD documents and handoffs, never a runtime; concurrent sessions, no locks. |
| `agentic-entities` | agentic-entities | The entity registry — three personas, the deterministic behaviours every harness implements, the rules — and the behavior map binding each skill to law. |

### distribution

| slug | title | tldr |
|------|-------|------|
| `public-asset-distribution` | public-asset-distribution | Public assets staged once, projected into the root map, scoped AGENTS.md, .agents/ and each registered harness's files; doctor reports drift. |
| `pypi-distribution` | pypi-distribution | The PyPI package on one version axis, two console-script names, the OIDC pipeline that also publishes the skills repo, the wheel contract and the docs site. |

### harness

| slug | title | tldr |
|------|-------|------|
| `harness-claude-code` | harness-claude-code | Entry harness with native sub-agent dispatch; reads the root AGENTS.md map natively and reaches skills and personas through per-entry symlinks into .agents/. |
| `harness-codex` | harness-codex | Entry harness on the Codex CLI: native AGENTS.md chain and .agents/skills; .codex/ carries config, hooks, the command policy and persona TOML. |
| `harness-copilot` | harness-copilot | Entry harness on GitHub Copilot CLI — native root AGENTS.md and .agents/skills; .github/ carries agents/*.agent.md transcodes and two hook files. |
| `harness-cursor` | harness-cursor | Entry harness on Cursor — native root AGENTS.md and .agents/skills; .cursor/ carries hooks.json (gate on shell, reaper at session start) and persona symlinks. |
| `harness-devin` | harness-devin | Entry harness on the Devin CLI — native AGENTS.md, .agents/skills and .agents/agents; its one projected file, .devin/hooks.v1.json, registers gate and reaper. |
| `harness-kimi-code` | harness-kimi-code | Entry harness with an empty projection: reads root AGENTS.md, .agents/skills and .agents/agents natively; user-level hook shims; DADAIA_CONTEXT binds. |

### philosophy

| slug | title | tldr |
|------|-------|------|
| `product-vision` | product-vision | One workspace folder, an agent at its root, projects in repos inside, governance outside every repo; multi-project x multi-repo, never a monorepo; no slop. |
| `spec-context-project` | spec-context-project | One canonical specs tree owned by one main repository, optionally spanning associated repos, bound per session and safe for visible concurrent work. |

### platform

| slug | title | tldr |
|------|-------|------|
| `capabilities` | capabilities | dadaia capabilities [--json] prints the installed provider's contract — distribution version, specs pattern version, status tokens, certification entry point. |
| `ci-preflight` | ci-preflight | dadaia ci preflight runs the library's CI checks locally — ruff format, ruff check, mypy --strict, lint-imports, pytest — and refuses outside the source repo. |
| `consumer-agent-support` | Consumer validation gate | A consumer-side validation agent running the shipped recipe on a real workspace is the release gate; no wheel publishes until every statement reports PASS. |
| `context-management` | context-management | ALIVE/DEAD registry of one main repo plus N associated repos; one resolution per call; a bind names the session's scope and drives memory injection. |
| `context-portability` | context-portability | dadaia export writes the workspace's context set to one file; dadaia import registers each unknown context DEAD elsewhere, ready for dadaia context alive. |
| `cross-platform-portability` | cross-platform-portability | Linux, macOS and Windows through one platform capability seam, injected adapters, Python hooks and cross-OS CI legs. |
| `server-registry` | server-registry | Dev-server port registry with TTL and PID tracking so parallel sessions never collide — one stdlib skill script over one JSON state file; no CLI verb. |
| `specs-migration` | specs-migration | dadaia specs upgrade walks a specs/ tree from pattern 6 to the canonical 7 and repairs template leftovers; dadaia migrate lifts a v1 context registry to v2. |
| `workspace-doctor` | workspace-doctor | dadaia doctor is the one compliance check — workspace, specs and ledgers sections, one line per finding, exit 1 with a fix line; --fix moves slop, TTL deletes. |
| `workspace-init` | workspace-init | Idempotent bootstrap — dadaia init <dir> --harness <name> [--repo <url>] — venv, zones, law, one harness; with --repo the first context ALIVE and bound. |

### sdd

| slug | title | tldr |
|------|-------|------|
| `audits-canon` | audits-canon | Audits are committed three-pillar reviews over a sha window, their findings moved by audit.py; decisions are decisions.jsonl records the operator accepts. |
| `backlog-ledger` | backlog-ledger | The operator's demand queue: BACKLOG.json active[] plus one histo record per exit; backlog.py writes it, dadaia doctor judges bound subjects. |
| `bug-ledger` | bug-ledger | One bug record per line in BUGS.jsonl, registered after operator confirmation, closed only by a transition carrying evidence; bugs.py writes it. |
| `release-lifecycle` | release-lifecycle | One live release grown by closed-scope candidates; release.py moves _RELEASE.json; closure is gated on a memory reconciliation; promote merges the release PR. |
| `sdd-gate-v3` | sdd-gate-v3 | No-lock enforcement — three gate blocks (root entry, non-venv command, PROTECTED or out-of-scope write), one fix line per BLOCK, chokepoints at the push. |
