# Memory Catalog — dadaia-workspace

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `.agents/skills/dd-spec-navigator/scripts/memory.py catalog generate`; other
> sections of this file are preserved verbatim.

## Feature catalog

### agents

| slug | title | tldr |
|------|-------|------|
| `agent-comms` | agent-comms | The handoff-v1 JSON contract agents emit, its validator behind `dadaia reports validate`, and ack-on-consume deletion with a one-day TTL. |
| `agent-orchestration` | agent-orchestration | Three dd- personas are leaf workers dispatched by the main thread; SDD documents, worktrees and handoffs carry the work, never an orchestration runtime. |
| `agentic-entities` | agentic-entities | One registry names three personas, five deterministic behaviors and two abstract rules; a behavior map assigns each shipped skill and scoped law to an owner. |

### distribution

| slug | title | tldr |
|------|-------|------|
| `agent-evals` | agent-evals | The library's own agent evals — two graded tasks run on the candidate wheel and a PyPI baseline by one dispatch-or-schedule workflow. |
| `public-asset-distribution` | public-asset-distribution | Public install stages packaged assets and projects shared law, agents, skills and every registered harness; public doctor reports projection drift. |
| `pypi-distribution` | pypi-distribution | The PyPI package on one version axis, two console-script names, the OIDC pipeline, the wheel contract and the derived docs. |

### harness

| slug | title | tldr |
|------|-------|------|
| `harness-claude-code` | harness-claude-code | Entry harness with native sub-agent dispatch; reads the root AGENTS.md map natively and reaches skills and personas through per-entry symlinks into .agents/. |
| `harness-codex` | harness-codex | Entry harness on the Codex CLI: native AGENTS.md chain and .agents/skills; .codex/ carries config, hooks, the command policy and persona TOML. |
| `harness-copilot` | harness-copilot | Entry harness on GitHub Copilot CLI — native root AGENTS.md and .agents/skills; .github/ carries agent transcodes and two hook files, bootstrap at start. |
| `harness-cursor` | harness-cursor | Entry harness on Cursor — native root AGENTS.md and .agents/skills; .cursor/hooks.json gates every tool, injects and reaps at start; persona symlinks. |
| `harness-devin` | harness-devin | Entry harness on the Devin CLI — native AGENTS.md, .agents/skills and .agents/agents; its one file, .devin/hooks.v1.json, wires gate, injection and reaper. |
| `harness-kimi-code` | harness-kimi-code | Entry harness with an empty projection: reads root AGENTS.md, .agents/skills and .agents/agents natively; user-level hook shims; DADAIA_CONTEXT binds. |

### philosophy

| slug | title | tldr |
|------|-------|------|
| `product-vision` | product-vision | One workspace keeps project repositories inside it and governance outside; each context spans one main repository and any associated repositories. |
| `spec-context-project` | spec-context-project | One canonical specs tree owned by one main repository, optionally spanning associated repos, bound per session and safe for visible concurrent work. |

### platform

| slug | title | tldr |
|------|-------|------|
| `capabilities` | capabilities | dadaia capabilities [--json] prints the installed contract: distribution and specs pattern versions, status tokens, the live verbs and harnesses. |
| `consumer-agent-support` | Consumer validation gate | A consumer-side agent running the developer's recipe on a real workspace is the release gate; no wheel publishes until every statement reports PASS. |
| `context-management` | context-management | ALIVE/DEAD registry of a main repo plus associated repos; create clones, hooks and ALIVEs; only context bind binds, by env session id, naming the scope. |
| `context-portability` | context-portability | dadaia export writes the workspace's context set to one file; dadaia import registers each unknown context DEAD elsewhere, ready for dadaia context alive. |
| `cross-platform-portability` | cross-platform-portability | Linux, macOS and Windows through one platform capability seam carrying the venv layout, Python hooks and cross-OS CI legs. |
| `server-registry` | server-registry | Dev-server port registry with TTL and PID tracking so parallel sessions never collide — one stdlib skill script over one JSON state file; no CLI verb. |
| `specs-migration` | specs-migration | specs init establishes canon and gitflow; specs upgrade reaches pattern 12; migrate updates the context registry. |
| `workspace-doctor` | workspace-doctor | dadaia doctor, the one compliance check — workspace, specs, ledgers; one line per finding, exit 1 with a fix line; --fix holds slop, expiry acts by zone class. |
| `workspace-init` | workspace-init | Level 1 — uvx dadaia-workspace init [DIR] provisions venv, zones, law, one harness; re-init upgrades; --repo adds level 2; next step from one ordered step list. |

### sdd

| slug | title | tldr |
|------|-------|------|
| `audits-canon` | audits-canon | An audit runs bug-history, spec-compliance and memory-drift pillars over one measured window and stores schema-valid findings until terminal disposition. |
| `backlog-ledger` | backlog-ledger | The operator's demand queue: BACKLOG.json active[] plus one histo record per exit; backlog.py writes it, dadaia doctor judges bound subjects. |
| `bug-ledger` | bug-ledger | BUGS.jsonl stores one lean current record per confirmed defect; its writer persists registration and resolution facts while git owns derived history. |
| `release-lifecycle` | release-lifecycle | One live release grows through closed-scope candidates; _RELEASE.json holds current phase, milestones and a lean append-only narrative. |
| `sdd-gate-v3` | sdd-gate-v3 | No-lock enforcement combines root-entry hygiene and SDD write policy before tools, then applies branch, specs-canon and privacy checks at push. |
| `worktrees` | worktrees | Repository changes are isolated in canonical plain, release, task, backlog or hotfix worktrees and land by worktree.py merge after the gate for that tree shape. |
