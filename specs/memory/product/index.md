# Product Memory — dadaia-workspace

## Vision

dadaia-workspace is a **multi-AI-harness × multi-project × SDD-oriented × multi-agent**
development workspace. It runs the same agent fleet across more than one AI coding harness
(Claude Code, Codex, and — when installed — OpenCode), over more than one software project
at once, under Spec-Driven Development, coordinated by a roster of specialized agents. Its
product is not any single project's code: it is the **workspace-level context-engineering**
that orients an otherwise generic agent fleet so those agents can build many projects safely,
in an organized way, and in parallel — without re-deriving how to work each time and without
colliding with one another.

The **Spec Context Project** (constitution §0) is the central concept and unit through which
this is delivered: one canonical specs folder bound to one repository, session-bindable,
enabling the bind → inject → enforce → parallel-multi-project value chain. See
[[spec-context-project]] for the full definition.

## Users

The operator who runs a dadaia workspace and the AI agents (project-manager, product-engineer,
software-engineer, the gate + audit personas, ai-engineer) that execute the development
lifecycle inside it. Each agent self-pulls the 1–3 atoms relevant to its task.

## Catalog

Features grouped by thematic area. Each link is a relative path to the atom.

<ol class="catalog">

**philosophy/** — foundational concepts and design stance
<li><a href="philosophy/spec-context-project.md">spec-context-project</a> — The keystone concept: one canonical specs folder + one repo, session-bindable, enabling safe parallel multi-project work (constitution §0)</li>
<li><a href="philosophy/repos-catalog.md">repos-catalog</a> — the spec-context repos catalog model</li>

**agents/** — the agent surface and how it runs
<li><a href="agents/agent-sdd-alignment.md">agent-sdd-alignment</a> — 9-core agents aligned to constitution §7 lifecycle phases; sub-agent model; dispatcher purity</li>
<li><a href="agents/agent-orchestration.md">agent-orchestration</a> — coordinator+sub-agent architecture; 9-core roster; 2 workflows; dispatcher purity</li>
<li><a href="agents/agent-monitoring.md">agent-monitoring</a> — local stdlib telemetry feeding the panel Agents/Workflows tabs</li>
<li><a href="agents/agent-comms.md">agent-comms</a> — the handoff-v1.1 contract + `dadaia reports` validation</li>
<li><a href="agents/harness-primitives.md">harness-primitives</a> — all-agent literacy on AI-entity primitives</li>
<li><a href="agents/ai-harness-claude-code.md">ai-harness-claude-code</a> — Claude Code harness decision protocols (ai-engineer)</li>
<li><a href="agents/ai-harness-codex.md">ai-harness-codex</a> — Codex harness decision protocols (ai-engineer)</li>
<li><a href="agents/ai-context-engineering.md">ai-context-engineering</a> — context-engineering craft (ai-engineer)</li>

**sdd/** — the spec-driven-development engine
<li><a href="sdd/sdd-gate-v3.md">sdd-gate-v3</a> — the PreToolUse path-classifier gate + single-record TTL-lease enforcement (v0.1.6)</li>
<li><a href="sdd/sdd-bug-backlog-governance.md">sdd-bug-backlog-governance</a> — bugs+backlog → release maturity model</li>
<li><a href="sdd/sdd-hotfix-track.md">sdd-hotfix-track</a> — the hotfix fast-lane track</li>
<li><a href="sdd/specs-doctor.md">specs-doctor</a> — structural SDD invariant validation</li>
<li><a href="sdd/quality-assurance.md">quality-assurance</a> — five-layer test architecture + CI split + no-slop policy</li>

**panel/** — the local control surface
<li><a href="panel/panel.md">panel</a> — the local web panel (servers, contexts, reports, memory, kanban)</li>
<li><a href="panel/brand-identity.md">brand-identity</a> — visual identity + design tokens</li>

**platform/** — workspace lifecycle and host integration
<li><a href="platform/context-management.md">context-management</a> — multi-context ALIVE/DEAD lifecycle + single-record TTL-lease (v0.1.6)</li>
<li><a href="platform/workspace-init.md">workspace-init</a> — workspace initialization</li>
<li><a href="platform/workspace-doctor.md">workspace-doctor</a> — runtime drift diagnosis + repair (v0.1.6 lock model)</li>
<li><a href="platform/workspace-portability.md">workspace-portability</a> — cross-host / cross-platform portability</li>
<li><a href="platform/server-registry.md">server-registry</a> — dev-server port registry</li>
<li><a href="platform/multi-platform-parity.md">multi-platform-parity</a> — Claude/Codex/opencode parity guarantees (9 agents / 17 skills / 2 workflows)</li>

**distribution/** — how the canonical surface ships
<li><a href="distribution/public-asset-distribution.md">public-asset-distribution</a> — `public/` → runtime projection (stage/install/doctor)</li>
<li><a href="distribution/academy.md">academy</a> — copy-from-template course system for onboarding</li>

</ol>

## Capability map

```mermaid
flowchart LR
    spec_context[Spec Context Project] --> sdd[sdd]
    spec_context --> agents[agents]
    agents --> sdd
    sdd --> distribution[distribution]
    agents --> distribution
    distribution --> platform[platform]
    platform --> panel[panel]
    agents --> panel
    philosophy --> spec_context
    philosophy --> agents
    philosophy --> sdd
```

## Limits

dadaia-workspace is **not**: an AI model provider (it orchestrates external harnesses, it
does not serve models); a CI/CD system (it gates and validates locally, but delegates
pipelines to GitHub Actions); a cloud service (it is a local-first library + CLI); a
general project-management tool (its scope is the SDD release lifecycle for code workspaces).
