# Dadaia Workspace: Product Vision

This document organizes the intended shape of `dadaia-workspace`. It is a
normative vision: it describes what the workspace must be, not a guarantee that
every behavior is already fully implemented.

## 1. Identity

`dadaia-workspace` is a Python library that creates an AI-native development
workspace for multi-project, multi-agent, Spec-Driven Development.

Its product is not one repo and not one assistant. Its product is the
workspace-level context engineering that turns generic AI coding agents into a
disciplined software team able to work safely, repeatedly, and in parallel.

The workspace combines:
1. A canonical scaffold.
2. Spec-Driven Development (SDD).
3. Spec Context Projects.
4. Multi-agent roles, skills, hooks, rules, and scoped `AGENTS.md`.
5. Multi-harness support for Claude Code, Codex, and Kimi Code.
6. Reports, handoffs, audits, memory, and a panel.
7. A strict anti-slop operating model.

## 2. Philosophy and Pillars

The core philosophy is simple:

1. Agents produce better work when the workspace gives them the right context.
2. Context must be structured, scoped, and discoverable instead of global and
   always-on.
3. Implementation must follow approved specs, not improvised intent.
4. Parallel work must be safe by construction.
5. Public agentic assets must stay generic and useful for any user.
6. Temporary, duplicated, misplaced, or low-value AI output is slop and must be
   prevented or contained.

The pillars are:

1. **Multi-harness development**: one canonical source projects agents, skills,
   rules, hooks, workflows, and instructions into Claude Code, Codex, Kimi Code,
   and generic agent surfaces.
2. **SDD as the operating model**: releases are defined before implementation
   through `SPEC.md`, `PLAN.md`, `TASKS.md`, and closed through `CLOSURE.md`.
3. **Spec Context Project as the keystone**: each session works inside one
   bound project context, with the right specs and memory.
4. **Context engineering by scope**: rules live where they matter; root
   instructions stay short; detailed behavior is discovered near the files it
   governs.
5. **Anti-slop by design**: the workspace protects roots, repos, specs, memory,
   tests, reports, and agentic assets from uncontrolled generated output.

## 3. Workspace Scaffold

The workspace root is not a git repo and must not become one. Repositories live
under `repos/`.

Allowed root entries are:

1. `.agents/`: universal agent assets and shared skills.
2. `.claude/`: Claude Code projection.
3. `.codex/`: Codex projection.
4. `.dadaia/`: operational data for the workspace.
6. `repos/`: alive repos associated with Spec Context Projects.
7. `AGENTS.md`: root workspace rules.
8. `CLAUDE.md`: Claude compatibility pointer where needed.
9. `prompt.md`: optional human-created long prompt file.

Agents must not create extra root files or folders. Human-created exceptions are
allowed, but agent behavior must default to root cleanliness.

`.dadaia/` is the operational home:

1. `.dadaia/.venv/`: workspace Python environment and CLI dependencies.
2. `.dadaia/handoff/`: machine-readable agent-to-agent communication.
3. `.dadaia/reports/`: human-readable HTML reports served by the panel.
4. `.dadaia/states/`: JSON state for workspace features.
5. `.dadaia/tmp/`: temporary output and short-lived agent artifacts.
6. `.dadaia/mcps/`: working areas for MCP-style tooling when needed.

Agents may read state files to understand the workspace, but durable state
changes must go through the CLI or proper feature interface, not manual JSON
editing.

`repos/` contains repositories that are currently ALIVE. A Spec Context Project
can be `ALIVE` when the repo exists on disk or `DEAD` when the workspace keeps
the context but removes the repo from disk. Moving from ALIVE to DEAD must be
safe: work must be committed and pushed before the repo is removed. If safety
cannot be proven, the repo must not be deleted.

## 4. Scoped Rules

Scoped `AGENTS.md` files are part of the product design. They keep instructions
small, local, and inspectable.

Expected scoped surfaces:
1. Root `AGENTS.md`: global workspace law and anti-slop root hygiene.
2. `.dadaia/AGENTS.md`: operational folder rules.
3. `.dadaia/handoff/AGENTS.md`: handoff paths and strict JSON contract.
4. `.dadaia/reports/AGENTS.md`: HTML report format, paths, and panel rules.
5. `.dadaia/states/AGENTS.md`: read-only state inspection and CLI-only mutation.
6. `.dadaia/tmp/AGENTS.md`: temporary artifact rules and cleanup expectations.
7. `specs/AGENTS.md`: SDD specs structure and lifecycle behavior.
8. `specs/memory/AGENTS.md`: memory consumption, ownership, and update rules.

A rule about reports belongs near reports. A rule about memory belongs near
memory. Root rules should point agents to scoped rules instead of duplicating
every detail.

## 5. Spec Context Project

The Spec Context Project is the keystone concept.

A Spec Context Project is one canonical specs folder bound to one main
repository. It can be bound to a terminal session, and that binding creates the
workspace value chain:

1. **Bind**: the session attaches to one project context.
2. **Inject**: constitution and memory orient the agent.
3. **Enforce**: SDD gates constrain production writes.
4. **Parallelize**: multiple projects advance safely in different sessions.

Without Spec Context Projects, agents rediscover context every time and can
collide across projects. With Spec Context Projects, each session knows which
project it serves and which specs govern it.

A context should normally have one main repo. Additional associated repos may
exist, but the main repo owns the canonical specs folder.

When a new context is created, the workspace scaffolds the canonical specs tree
in the main repo. If a conflicting `specs/` already exists, it must be preserved
safely before the canonical structure is created.

## 6. Canonical Specs and Memory

Each Spec Context Project owns this specs tree:

1. `specs/backlog/`: product ideas and backlog candidates.
2. `specs/bugs/`: user-reported or agent-detected bugs.
3. `specs/releases/`: versioned release definitions and lifecycle artifacts.
4. `specs/memory/`: current product truth.
5. `specs/audits/`: committed audit findings.
6. `specs/constitution.md`: highest local product law.
7. `specs/AGENTS.md`: scoped instructions for agents working with specs.

Memory is one of the most important parts of the model. It describes current
truth, not history. History belongs in release closures and archives.

Canonical memory includes:
1. `specs/memory/architecture.md`: architecture truth.
2. `specs/memory/tech-stack.md`: concise approved toolchain and dependencies.
3. `specs/memory/quality-assurance.md`: test architecture, coverage view, and
   quality strategy.
4. `specs/memory/product/`: product truth organized by feature.

Large product memory must be optimized for context. Agents should receive a
small deterministic bootstrap and then pull detailed feature atoms on demand.
The product memory tree should stay shallow and navigable, with a machine-
readable map or catalog that explains where feature knowledge lives.

Memory updates must be strict. Only the right lifecycle phase and role can
change memory, because future agents will treat memory as truth.

## 7. Development Lifecycle

The workspace manages the full development lifecycle:

1. Research.
2. Bug reporting.
3. Backlog definition.
4. Release definition.
5. Implementation.
6. Review gates.
7. Closure and memory update.
8. Audits.

Each phase has a clear owner, allowed write target, and concurrency behavior.

### 7.1 Research

Research is read-only with respect to production and specs truth. Users can bind
a session to a Spec Context Project and ask questions or request reports.
Research output is written as HTML under `.dadaia/reports/` and shown in the
panel. Research may run in parallel; timestamped report paths avoid collisions.

The project-manager may coordinate research and ask specialist agents for input,
but the final report should have one clear owner.

### 7.2 Bug Reporting

Bugs are registered under `specs/bugs/` for the bound Spec Context Project. Bugs
may come from the user or from an agent that discovers a defect during work. Bug
filing is additive and may run in parallel when naming avoids collisions.

### 7.3 Backlog Definition

Backlog definition turns user ideas into organized product candidates.

The project-manager owns backlog writing. It must inspect existing backlog,
bugs, releases, and memory before creating new backlog. If a request duplicates
or subsumes existing work, the existing item should be updated or referenced
instead of creating slop.

Ambiguous ideas should go through a `dadaia-grill-me` refinement session before
they become backlog.

### 7.4 Release Definition

Release definition converts backlog, bugs, and user demand into a concrete
release. The project-manager coordinates; the product-engineer writes
`SPEC.md`, `PLAN.md`, and `TASKS.md`.

Releases use versioned folders under `specs/releases/`, such as
`specs/releases/vMAJOR.MINOR.PATCH/`.

Release definition is mutating. Only one session may define a release for the
same Spec Context Project at a time, across all harnesses.

After approval, covered backlog and bug items must be removed, closed, or
clearly marked as consumed so they do not survive as slop.

### 7.5 Implementation and Review

Implementation is mutating and serialized per Spec Context Project.

The project-manager coordinates. The software-engineer implements production
code and tests according to the approved release and reserved tasks.

Review gates are additive evidence gates:

1. `qa-engineer`: commit gate; validates tests, coverage, E2E evidence, and spec
   alignment.
2. `security-reviewer`: push gate; checks vulnerabilities, secrets, dependency
   risk, and security regressions.
3. `code-reviewer`: PR gate; checks diffs, architecture consistency, release
   intent, maintainability, and implementation quality.

After review approval, the product-engineer closes the release, updates memory,
archives the release, and prepares the project for the next cycle.

## 8. Parallelism and Concurrency

The concurrency model must be simple:

1. Avoid race conditions.
2. Avoid deadlocks.
3. Avoid manual lock rituals.
4. Preserve safe parallelism where work is additive.

ADDITIVE phases can run in parallel because they write reports, handoffs, bugs,
backlog, or audit evidence.

MUTATING phases must be serialized because they change release definitions,
production code, tests, memory, or active release state.

The workspace must enforce at most one mutating session per Spec Context Project
while allowing many read-only or additive sessions.

## 9. Agent Model

Agents are generic public roles specialized for the SDD flow, not for a
private domain.

Good agents have narrow responsibility, clear lifecycle ownership, role-specific
skills, direct instructions, and no private project knowledge in public defaults.

Core roles:

1. `project-manager`: coordinates the lifecycle and knows when to involve each
   specialist.
2. `project-auditor`: performs whole-project audits and fans out specialist
   review where appropriate.
3. `product-engineer`: owns specs, releases, memory update, and closure.
4. `software-engineer`: implements production code and tests under SDD
   discipline.
5. `ai-engineer`: owns multi-harness agentic surfaces, prompts, skills, rules,
   hooks, and runtime compatibility.
6. `software-architect`: reviews architecture, design patterns, and system
   shape.
7. `qa-engineer`: owns quality gates and test architecture review.
8. `security-reviewer`: prevents secrets, vulnerabilities, and unsafe changes
   from reaching public repos.
9. `code-reviewer`: protects PR quality, maintainability, and architectural
   consistency.

Only dispatcher roles should dispatch other agents. Worker agents should surface
needs to the dispatcher instead of creating uncontrolled chains.

## 10. Public Assets

Public agents, skills, rules, hooks, commands, templates, and scoped
instructions must be generic.

They must not include private repo names, customer data, operator-specific data,
domain-specific agents for one user's workflow, specialized unrelated skills, or
conflicting instructions across surfaces.

Domain-specific capability belongs in optional packs or private overlays. The
default public workspace should teach only the dadaia workflow and broadly useful
software engineering behavior.

Agentic assets must be direct and inspectable. A simple behavior should be
stated in one clear rule, not hidden in verbose prose.

## 11. Reports, Handoffs, Audits, and Panel

The workspace has distinct communication channels:

1. `.dadaia/reports/`: HTML reports for humans, served in the panel.
2. `.dadaia/handoff/`: machine-readable JSON handoffs between agents.
3. `specs/audits/`: committed audit results for the Spec Context Project.

These channels must not duplicate the same fact in conflicting places. Each has
one purpose and one canonical destination.

The panel is the user-facing visibility layer. It should show workspace state,
contexts, reports, handoffs, servers, sessions, workflows, agents, and relevant
project information with the dadaia visual identity.

## 12. What Dadaia Workspace Must Avoid

`dadaia-workspace` must not become:

1. A loose folder full of generated files.
2. A repo-root dumping ground.
3. A set of verbose global prompts.
4. A collection of private, domain-specific agents.
5. A system where agents bypass specs because a request sounds urgent.
6. A system where backlog, bugs, releases, and memory duplicate each other.
7. A system where parallel agent sessions can corrupt the same project.

The workspace succeeds when it stays simple, scoped, deterministic, and clean.

## 13. Desired End State

The ideal `dadaia-workspace` lets a user manage many software projects with many
AI sessions safely.

For each project, the user creates or activates a Spec Context Project. The
workspace scaffolds the specs pattern, binds sessions to the right context,
injects the right memory, enforces SDD, coordinates agents, records reports and
handoffs, protects memory, and keeps slop contained.

The result should feel like a professional AI-native development environment:
simple at the surface, strict where correctness matters, and optimized for agents
to do high-quality work without drifting away from the user's intent.
