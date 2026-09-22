---
slug: product-vision
title: product-vision
tldr: One workspace folder, an agent at its root, projects in repos inside, governance outside every repo; multi-project x multi-repo, never a monorepo; no slop.
summary: The founding paradigm and the pillars of dadaia-workspace, plus the two usage paths (a human from a shell, an agent from the root AGENTS.md map).
tags: [vision, paradigm, pillars]
sources:
  - AGENTS.md
  - dadaia_workspace/public/data/AGENTS.md
  - specs/constitution.md
---

## The paradigm

- One workspace folder; the agent session launches at its root, always.
- Projects live in repos inside it (`repos/<slug>/`); governance — the root `AGENTS.md` map, the scoped `AGENTS.md`, `.agents/skills`, `.agents/agents`, `.dadaia/` — lives outside every repo.
- A project is a context: one **main repo**, where `specs/` lives, plus its **associated repos**; a workspace holds many contexts and a context holds many repos — never a monorepo; a single-repo context is the degenerate case ([[spec-context-project]], [[context-management]]).
- Canonical rules steer every session away from slop; the same rules reach every harness through the one authored set ([[agentic-entities]]).

## Identity and pillars

- dadaia-workspace is the operating environment around repositories developed with AI agents, its unit being the context.
- Current context — agents bind explicitly and receive only the relevant project, memory, release and task state.
- Documents are the lifecycle — backlog, SPEC, PLAN, TASKS, `_RELEASE.json` and `BUGS.jsonl` carry ordered work, and the workspace ships no runtime driving agents through steps.
- Deterministic boundaries — path class, bind scope, root hygiene, venv-rooting and the git push gate are mechanical, each refusal carrying its own runnable fix; what cannot be mechanical is written as law ([[sdd-gate-v3]]).
- Visible concurrency — sessions may race, git exposes overlap, and nothing freezes waiting on a lock.
- No mechanism without a demand — a capability exists only while it earns its maintenance cost, and deleted surface beats accreted surface.
- No slop — runtime state, reports, handoffs, caches, projections and temporary files have canonical homes and never leak into repositories.
- Claude Code, Codex, Kimi Code, Cursor, Devin and GitHub Copilot are Layer-1 entry harnesses, one registry record each; public assets originate once, stage once, and the authored set is read natively or through per-entry symlinks ([[public-asset-distribution]]).
- Success is evidenced by reviews, task markers, commands and artifacts, never inferred from prose.

## Two usage paths

- A human installs it from PyPI and drives it from a shell: `dadaia init <dir> --harness <name> --repo <url>` provisions a workspace with its first project ALIVE and bound in one line (`context create --main-repo`/`alive`/`bind` add the next ones), `dadaia doctor` lists findings with a runnable fix under every refusal; `README.md` is that path, derived from memory ([[pypi-distribution]], [[workspace-init]], [[workspace-doctor]]).
- An agent reads the root `AGENTS.md` map — flow, roles, gate invariants, where things live, and the index of every scoped law and skill — opens the scoped `AGENTS.md` of the area it works in, and works inside the gate, the record verbs and the handoff contract; `llms.txt` at the repository root is its index ([[sdd-gate-v3]], [[agent-comms]]).
- Both paths read one truth: every human- and agent-facing document derives from a named memory atom under its content hash ([[QUALITY]] P-29).

## Dependencies

[[spec-context-project]], [[context-management]], [[sdd-gate-v3]], [[ARCHITECTURE]], [[public-asset-distribution]], [[pypi-distribution]], [[QUALITY]], [[agentic-entities]].
