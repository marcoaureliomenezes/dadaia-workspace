---
slug: product-vision
title: product-vision
tldr: One workspace folder, an agent at its root, projects in repos inside, governance outside every repo; multi-project x multi-repo, never a monorepo; no slop.
summary: The founding paradigm and the pillars of dadaia-workspace, plus the two usage paths — a human from a shell, an agent from the root AGENTS.md map — reading one truth.
tags: [vision, paradigm, pillars]
sources:
  - AGENTS.md
  - dadaia_workspace/public/data/AGENTS.md
  - specs/constitution.md
---

## The paradigm

- One workspace folder; the agent session launches at its root, always.
- Projects live in repos inside it (`repos/<slug>/`); governance — the root `AGENTS.md` map, the scoped `AGENTS.md` files, `.agents/skills`, `.agents/agents`, `.dadaia/` — lives outside every repo.
- A project is a context: one main repo, where `specs/` lives, plus its associated repos; a workspace holds many contexts and a context many repos — never a monorepo; a single-repo context is the minimal case ([[spec-context-project]], [[context-management]]).
- The same canonical rules reach every harness through the one authored set ([[agentic-entities]]).

## Identity and pillars

- dadaia-workspace is the operating environment around repositories developed with AI agents; its unit is the context.
- Current context — agents bind explicitly and receive only the relevant project, memory, release and task state.
- Documents are the lifecycle — backlog, SPEC, PLAN, TASKS, `_RELEASE.json` and `BUGS.jsonl` carry ordered work; no runtime drives agents through steps ([[release-lifecycle]], [[bug-ledger]], [[backlog-ledger]]).
- Deterministic boundaries — path class, bind scope, root hygiene, venv-rooting and the push gate are mechanical, each refusal carrying its own runnable fix; what cannot be mechanical is written as law ([[sdd-gate-v3]]).
- Visible concurrency — sessions may race, git exposes overlap, and nothing waits on a lock.
- No mechanism without a demand — a capability exists only while it earns its maintenance cost, and deleted surface beats accreted surface.
- No slop — runtime state, reports, handoffs, caches, projections and temporary files have canonical homes and never leak into repositories.
- Claude Code, Codex, Kimi Code, Cursor, Devin and GitHub Copilot are the entry harnesses, one registry record each; public assets originate once, stage once, and are read natively or through per-entry symlinks ([[public-asset-distribution]]).
- Success is evidenced by reviews, task markers, commands and artifacts, never inferred from prose.

## Two usage paths

- A human drives it from a shell in three onboarding levels: `uvx dadaia-workspace init [DIR] --harness <name> --repo <url>` provisions the workspace with its first project cloned, hooked, ALIVE and bound; `.dadaia/.venv/bin/dadaia specs init --context <ctx>` gives the main repo its canonical `specs/`; `.dadaia/.venv/bin/dadaia context create --main-repo <url>` adds the next project; `.dadaia/.venv/bin/dadaia doctor` lists findings with a runnable fix under each and names the next step; re-running the `uvx` init line upgrades the workspace; `README.md` is that path ([[pypi-distribution]], [[workspace-init]], [[context-management]], [[workspace-doctor]]).
- The root `AGENTS.md` map carries the three levels in its onboarding section, and every command it and the scoped law cite runs through `.dadaia/.venv/bin/dadaia`.
- An agent reads the root `AGENTS.md` map — flow, roles, gate invariants, where things live, the index of every scoped law and skill — opens the scoped `AGENTS.md` of its area, and works inside the gate, the ledger scripts and the handoff contract; `llms.txt` at the repository root is its index ([[sdd-gate-v3]], [[agent-comms]]).
- Both paths read one truth: every human- and agent-facing document derives from a named memory atom under its content hash ([[QUALITY]] P-29).

## Dependencies

[[spec-context-project]], [[context-management]], [[sdd-gate-v3]], [[release-lifecycle]], [[bug-ledger]], [[backlog-ledger]], [[ARCHITECTURE]], [[public-asset-distribution]], [[pypi-distribution]], [[QUALITY]], [[agentic-entities]].
