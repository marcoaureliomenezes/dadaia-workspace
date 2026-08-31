# Memory Catalog — dadaia-workspace

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `dadaia memory catalog generate`; other
> sections of this file are preserved verbatim.

## Catálogo de features

### agents

| slug | title | tldr |
|------|-------|------|
| `agent-comms` | agent-comms | The handoff-v1 JSON contract agents emit, its stdlib validator behind `dadaia reports`, and ack-on-consume deletion. |
| `agent-monitoring` | agent-monitoring | Stdlib-only local agent telemetry behind an allowlist gate, plus the event-driven lifecycle of every runtime artifact under .dadaia/. |
| `agent-orchestration` | agent-orchestration | Nine core Layer-1 roles, two dispatchers, document-governed ordered work, and advisory-only concurrency. |
| `agentic-entities` | agentic-entities | Abstract-entity registry — Personas, Behaviors, Rules — plus the behavior map binding every skill and scoped rule file to one law section. |

### distribution

| slug | title | tldr |
|------|-------|------|
| `academy` | academy | Packaged knowledge-base modules browsable in the panel's Academy tab, with a copy-from-template CLI for derived courses. |
| `public-asset-distribution` | public-asset-distribution | Canonical public assets staged to .dadaia/agentic and projected to the Claude Code, Codex, Kimi Code and .agents roots, hash-compared by doctor. |
| `pypi-distribution` | pypi-distribution | The published PyPI package on one version axis, the OIDC publish pipeline, and the wheel content contract. |

### harness

| slug | title | tldr |
|------|-------|------|
| `harness-claude-code` | Harness — Claude Code | Entry harness with native sub-agent dispatch; its scaffold is the CLAUDE.md bridge plus the .claude/ projection. |
| `harness-codex` | Harness — Codex | Entry harness on the operator's Codex CLI — native AGENTS.md, Starlark command policy, version-qualified hook fire, `.codex/` projection. |
| `harness-kimi-code` | Harness — Kimi Code | Layer-1 harness — inert `.kimi-code/` projection plus user-level TOML hook shims; binds through `DADAIA_CONTEXT` exported at launch. |

### panel

| slug | title | tldr |
|------|-------|------|
| `brand-identity` | brand-identity | The panel's canonical five-colour palette and its CSS token mapping, sourced only from `views/assets/css/tokens.py`. |
| `panel` | panel | Local loopback-only six-tab workspace UI — Projects, Agents, Agentic Entities, Reports, Academy, Servers. |

### philosophy

| slug | title | tldr |
|------|-------|------|
| `product-vision` | product-vision | A local-first, strictly bounded SDD workspace giving agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries. |
| `spec-context-project` | spec-context-project | One canonical specs tree owned by one main repository, optionally spanning associated repos, bound per session and safe for visible concurrent work. |

### platform

| slug | title | tldr |
|------|-------|------|
| `consumer-agent-support` | Consumer validation gate | A consumer-side validation agent running the shipped recipe on a real workspace is the release gate; no wheel publishes without its CERTIFIED_100 verdict. |
| `context-management` | context-management | ALIVE/DEAD registry of one main repo plus N associated repos, one Invocation resolved per process, bind-driven injection, advisory presence, redactable output. |
| `cross-platform-portability` | cross-platform-portability | Linux, macOS and Windows through one platform capability seam, injected adapters, Python hooks and hard-gated cross-OS CI legs. |
| `server-registry` | server-registry | Port registry with TTL and PID tracking so parallel agents' dev servers never collide; the 3000-3999 range binds only `next_port`. |
| `workspace-doctor` | workspace-doctor | Diagnoses root hygiene, venv health, context coherence, slug-ownership collisions, stale presence and lock residue; repairs deterministic state only. |
| `workspace-init` | workspace-init | Idempotent bootstrap of workspace state, the Python venv, the selected harness projections and the governance hooks. |

### sdd

| slug | title | tldr |
|------|-------|------|
| `audits-canon` | audits-canon | Audits are committed spec artifacts — three pillars over a sha window, findings as JSONL records, dispositioned by exactly one remediation release. |
| `sdd-bug-backlog-governance` | sdd-bug-backlog-governance | One record per bug through one write seam, a live-photo backlog with histo exits, and the _RELEASE.json state document. |
| `sdd-gate-v3` | sdd-gate-v3 | No-lock enforcement — origin-classified LAW, path/phase/mode gates, phase read from _RELEASE.json, git hooks pared to the publication boundary. |
| `specs-doctor` | specs-doctor | Validates the v6 canon tree, memory drift and catalog integrity, _RELEASE.json, bug and backlog governance, and audit findings folded from JSONL. |

