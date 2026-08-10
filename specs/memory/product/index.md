# Memory Catalog — dadaia-workspace

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `dadaia memory catalog generate`; other
> sections of this file are preserved verbatim.

## Catálogo de features

### agents

| slug | title | tldr |
|------|-------|------|
| `agent-comms` | agent-comms — Handoff Contract v1 | handoff-v1.2 separates HTML reports from JSON handoffs and carries the self_pull Layer-1 read-proof line. |
| `agent-monitoring` | agent-monitoring | stdlib-only local telemetry (Claude/Codex/PI sessions) → panel Sessions tab + /api/agents; allowlist gate preserves privacy. |
| `agent-orchestration` | agent-orchestration | Nine core Layer-1 roles, two dispatchers, document-governed ordered work, and advisory-only concurrency. |

### distribution

| slug | title | tldr |
|------|-------|------|
| `academy` | academy | browsable knowledge_basis in the panel's Academy tab + copy-from-template management via CLI. |
| `plugin-packs` | plugin-packs | in-package plugin packs (4 skills each) enabled via `dadaia plugin install`, disabled via `uninstall`; 3 stub agents gain real behavior once installed. |
| `public-asset-distribution` | public-asset-distribution | canonical public assets are staged to .dadaia/agentic and projected to Claude Code, Codex, PI, and shared .agents roots. |
| `pypi-distribution` | pypi-distribution | The published dadaia-workspace 0.2.x PyPI package, the release.yml OIDC publish pipeline, the wheel content contract, and the SDD-vs-package version split. |

### harness

| slug | title | tldr |
|------|-------|------|
| `harness-claude-code` | Harness — Claude Code | Entry harness with native sub-agent dispatch; scaffold = CLAUDE.md bridge + .claude/ projection. |
| `harness-codex` | Harness — Codex | Entry harness on the operator's Codex subscription: TUI with deterministic hooks, Starlark command policy, and a .codex/ projection of agents, skills and rules. |
| `harness-kimi-code` | Harness — Kimi Code | Layer-1-only harness: `.kimi-code/` projection + hooks via a managed block in the user-level `config.toml`; first with post-compact re-injection. |
| `harness-pi` | Harness - PI (pi-coding-agent) | Entry harness with a trusted TypeScript gate extension projected into .pi/, plus allowlisted PI session telemetry. |

### panel

| slug | title | tldr |
|------|-------|------|
| `brand-identity` | brand-identity | canonical 5-color palette and CSS tokens of the panel (release dadaia-workspace-brand-identity-v1). |
| `panel` | panel | Local five-tab panel with agent model governance, telemetry, reports, academy, and servers. |

### philosophy

| slug | title | tldr |
|------|-------|------|
| `product-vision` | product-vision | A strict, portable SDD workspace that gives agents current context, a document-governed lifecycle, visible concurrency, and strong anti-slop boundaries. |
| `spec-context-project` | spec-context-project | One canonical specs tree plus one repository, explicitly bindable by each session and safe for visible concurrent work. |

### platform

| slug | title | tldr |
|------|-------|------|
| `consumer-agent-support` | Consumer validation gate — supported consumer environments | A consumer-side validation agent running the shipped recipe is the release gate: no wheel is published without its CERTIFIED_100 verdict. |
| `context-management` | context-management | ALIVE/DEAD context registry, caller-owned session binding, bind-driven memory injection, and advisory presence with no concurrency locks. |
| `cross-platform-portability` | cross-platform-portability | Linux, macOS, and Windows support through a single platform capability seam, injected adapters, Python hooks, and hard-gated cross-OS tests. |
| `multi-platform-parity` | multi-platform-parity | Claude Code, Codex, and PI receive truthful runtime-specific projections from one canonical public source. |
| `repos-catalog` | repos-catalog | repos.xlsx lookup for fast discovery of known repos with slug + URL. |
| `server-registry` | server-registry | internal port registry with TTL+PID to avoid conflicts between parallel agents' dev servers; the 3000-3999 range applies only to next_port allocation. |
| `workspace-doctor` | workspace-doctor | Diagnoses root hygiene, venv health, context coherence, stale presence, and retired lock-state residue; repairs only deterministic state. |
| `workspace-init` | workspace-init | Idempotent bootstrap of workspace state, Python venv, selected harness projections, and governance hooks. |
| `workspace-portability` | workspace-portability | export/import of the whole workspace as a tar.gz for backup or migration between machines. |

### sdd

| slug | title | tldr |
|------|-------|------|
| `sdd-bug-backlog-governance` | sdd-bug-backlog-governance | Event-sourced JSONL bugs, PM-curated backlog, release consumption, audit dispositions, and exact-commit security-gated push. |
| `sdd-gate-v3` | sdd-gate-v3 | No-lock SDD enforcement: deterministic path/mode gates, advisory presence, warn-only concurrent commits, and a security-gated push boundary. |
| `specs-doctor` | specs-doctor | Validates canonical specs structure, memory/catalog integrity, release markers, closure evidence, dispositions, bug ledgers, and audit coherence. |
