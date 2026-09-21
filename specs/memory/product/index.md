# Memory Catalog — dadaia-workspace

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `.agents/skills/dd-spec-navigator/scripts/memory.py catalog generate`; other
> sections of this file are preserved verbatim.

## Feature catalog

### agents

| slug | title | tldr |
|------|-------|------|
| `agent-comms` | agent-comms | The handoff-v1 JSON contract agents emit, its stdlib validator behind `dadaia reports`, and ack-on-consume deletion. |
| `agent-orchestration` | agent-orchestration | Nine core Layer-1 roles, two dispatchers, document-governed ordered work, and advisory-only concurrency. |
| `agentic-entities` | agentic-entities | Abstract-entity registry — Personas, Behaviors, Rules — plus the behavior map binding every skill and scoped rule file to one law section. |

### distribution

| slug | title | tldr |
|------|-------|------|
| `brand-identity` | brand-identity | The brand — the dadaia-workspace slug, the rhino mark and the five-colour palette — for the docs site and launch assets; no in-package UI carries it any more. |
| `public-asset-distribution` | public-asset-distribution | Public assets staged once, projected into the authored set (root map, scoped AGENTS.md, .agents/skills, .agents/agents); .claude/ entries are symlinks. |
| `pypi-distribution` | pypi-distribution | The published PyPI package on one version axis, the OIDC publish pipeline, and the wheel content contract. |

### harness

| slug | title | tldr |
|------|-------|------|
| `harness-claude-code` | harness-claude-code | Entry harness with native sub-agent dispatch; reads the root AGENTS.md map natively and reaches skills and personas through per-entry symlinks into .agents/. |
| `harness-codex` | harness-codex | Entry harness on the Codex CLI — native AGENTS.md chain and .agents/skills; .codex/ carries config, hooks, Starlark rules and the persona TOML transcode. |
| `harness-kimi-code` | harness-kimi-code | Layer-1 harness with an empty projection set — reads root AGENTS.md, .agents/skills and .agents/agents natively; user-level hook shims; DADAIA_CONTEXT binding. |

### philosophy

| slug | title | tldr |
|------|-------|------|
| `product-vision` | product-vision | One workspace folder, an agent at its root, projects in repos inside, governance outside every repo; multi-project x multi-repo, never a monorepo; no slop. |
| `spec-context-project` | spec-context-project | One canonical specs tree owned by one main repository, optionally spanning associated repos, bound per session and safe for visible concurrent work. |

### platform

| slug | title | tldr |
|------|-------|------|
| `consumer-agent-support` | Consumer validation gate | A consumer-side validation agent running the shipped recipe on a real workspace is the release gate; no wheel publishes until every statement reports PASS. |
| `context-management` | context-management | ALIVE/DEAD registry of one main repo plus N associated repos, one Invocation per process, a Bind carrying scope, bind-driven injection. |
| `cross-platform-portability` | cross-platform-portability | Linux, macOS and Windows through one platform capability seam, injected adapters, Python hooks and hard-gated cross-OS CI legs. |
| `server-registry` | server-registry | Port registry with TTL and PID tracking so parallel agents' dev servers never collide, owned by one stdlib script under the dd-cli-library skill. |
| `workspace-doctor` | workspace-doctor | The one compliance surface — dadaia doctor scores workspace, specs and ledgers from one rule record; --fix is the reaper, moving slop, deleting only by TTL. |
| `workspace-init` | workspace-init | Idempotent bootstrap of workspace state, the Python venv, the selected harness projections and the governance hooks. |

### sdd

| slug | title | tldr |
|------|-------|------|
| `audits-canon` | audits-canon | Audits are committed spec artifacts — three pillars over a sha window, JSONL findings moved by audit.py disposition, archived by audit.py close. |
| `sdd-bug-backlog-governance` | sdd-bug-backlog-governance | One bug record shape with no derived cache, one verb per governance record change, and every committed record schema-validated by dadaia doctor. |
| `sdd-gate-v3` | sdd-gate-v3 | No-lock enforcement — three gate blocks (root entry, non-venv command, PROTECTED or out-of-scope write), one fix line per BLOCK, chokepoints at the push. |
