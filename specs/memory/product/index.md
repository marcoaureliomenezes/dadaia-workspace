# Memory Catalog — dadaia-workspace

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `dadaia memory catalog generate`; other
> sections of this file are preserved verbatim.

## Catálogo de features

### agents

| slug | title | tldr |
|------|-------|------|
| `agent-comms` | agent-comms — Handoff Contract v1 | handoff-v1.2 separates HTML reports from JSON handoffs, carries the self_pull Layer-1 read-proof line, and dies on consumption unless it is artifact-bearing. |
| `agent-monitoring` | agent-monitoring | stdlib-only local telemetry → panel Sessions tab + /api/agents; allowlist gate preserves privacy; artifacts die event-driven, logs self-rotate. |
| `agent-orchestration` | agent-orchestration | Nine core Layer-1 roles, two dispatchers, document-governed ordered work, and advisory-only concurrency. |
| `agentic-entities` | agentic-entities | Abstract-entity registry — Personas, Behaviors, Rules; one rules-skills map with one enforcer; the measured always-on budget. |

### distribution

| slug | title | tldr |
|------|-------|------|
| `academy` | academy | browsable knowledge_basis in the panel's Academy tab + copy-from-template management via CLI. |
| `public-asset-distribution` | public-asset-distribution | canonical public assets, whole skill folders included, staged to .dadaia/agentic and projected to Claude Code, Codex, Kimi Code and .agents roots. |
| `pypi-distribution` | pypi-distribution | The published PyPI package on one version axis, the OIDC publish pipeline, the minted-unpublished shape, and the wheel content contract. |

### harness

| slug | title | tldr |
|------|-------|------|
| `harness-claude-code` | Harness — Claude Code | Entry harness with native sub-agent dispatch; scaffold = CLAUDE.md bridge + .claude/ projection. |
| `harness-codex` | Harness — Codex | Entry harness on the operator's Codex subscription: TUI and headless exec, version-qualified live-certified hook fire, Starlark policy, .codex/ projection. |
| `harness-kimi-code` | Harness — Kimi Code | Layer-1-only harness: `.kimi-code/` projection + user-level TOML hook shims; binds through `DADAIA_CONTEXT` at launch. |

### panel

| slug | title | tldr |
|------|-------|------|
| `brand-identity` | brand-identity | canonical 5-color palette and CSS tokens of the panel (release dadaia-workspace-brand-identity-v1). |
| `panel` | panel | Local six-tab panel with agent model governance, agentic entities, telemetry, reports, academy, and servers. |

### philosophy

| slug | title | tldr |
|------|-------|------|
| `product-vision` | product-vision | A strict, portable SDD workspace that gives agents current context, a document-governed lifecycle, visible concurrency, and strong anti-slop boundaries. |
| `spec-context-project` | spec-context-project | One canonical specs tree owned by one main repository, optionally spanning associated repos, bindable per session and safe for visible concurrent work. |

### platform

| slug | title | tldr |
|------|-------|------|
| `consumer-agent-support` | Consumer validation gate — supported consumer environments | A consumer-side validation agent running the shipped recipe is the release gate: no wheel is published without its CERTIFIED_100 verdict. |
| `context-management` | context-management | ALIVE/DEAD registry of one main repo plus N associated repos, one resolution authority, one repo accessor, lean bind-driven injection, advisory presence. |
| `cross-platform-portability` | cross-platform-portability | Linux, macOS, and Windows support through a single platform capability seam, injected adapters, Python hooks, and hard-gated cross-OS tests. |
| `multi-platform-parity` | multi-platform-parity | Claude Code, Codex, and Kimi Code receive truthful runtime-specific projections from one canonical public source. |
| `repos-catalog` | repos-catalog | repos.xlsx lookup for fast discovery of known repos with slug + URL. |
| `server-registry` | server-registry | internal port registry with TTL+PID to avoid conflicts between parallel agents' dev servers; the 3000-3999 range applies only to next_port allocation. |
| `workspace-doctor` | workspace-doctor | Diagnoses root hygiene, venv health, context coherence, slug-ownership collisions, stale presence, lock residue; repairs deterministic state only. |
| `workspace-init` | workspace-init | Idempotent bootstrap of workspace state, Python venv, selected harness projections, and governance hooks. |
| `workspace-portability` | workspace-portability | export/import of the whole workspace as a tar.gz for backup or migration between machines. |

### sdd

| slug | title | tldr |
|------|-------|------|
| `sdd-bug-backlog-governance` | sdd-bug-backlog-governance | JSONL bugs written through one sanitize-then-mask seam, a three-field evidence gate, an operator-gated backlog, the rc ladder and the git contract. |
| `sdd-gate-v3` | sdd-gate-v3 | No-lock SDD enforcement — origin-classified LAW, path/mode gates, advisory presence, feature-only push boundary with scan, verdict as PR gate. |
| `specs-doctor` | specs-doctor | Validates canonical specs structure, memory/catalog and placeholder integrity, release/segment markers, closure evidence, dispositions, bugs, and audits. |

