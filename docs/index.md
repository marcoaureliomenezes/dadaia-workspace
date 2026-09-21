# dadaia-workspace

A local-first, spec-driven workspace that gives AI agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.

Start here:

- [Quickstart](quickstart.md) — five minutes from `pip install` to a bound project, a backlog entry and a live release.
- [Positioning](positioning.md) — why your product repos never carry agent config, and how one law governs ten projects.
- [The bug loop](bug-loop.md) — register, RED test, fix, resolve with evidence and lineage.

Reference: [concepts](concepts.md) · [getting started](getting-started.md) · [CLI](cli.md) · [distribution](distribution.md).

Repository: <https://github.com/marcoaureliomenezes/dadaia-workspace> ·
skills, packaged standalone: <https://github.com/marcoaureliomenezes/dadaia-skills>

## What it is

<!-- derived-from: product-vision sha256:89dc2ce6898d -->

dadaia-workspace is the operating environment around repositories developed with AI
agents, and its unit is the context.

A workspace is one folder. The agent session launches at its root, always. Projects
live in repos inside it (`repos/<slug>/`) and the governance — the root `AGENTS.md`
map, the scoped `AGENTS.md` files, `.agents/skills`, `.agents/agents`, `.dadaia/` —
lives outside every repo. One workspace holds many contexts and a context holds many
repos; it is never a monorepo, and a single-repo context is the degenerate case.

What it rests on:

- Current context — agents bind explicitly and receive only the relevant project,
  memory, release and task state.
- Documents are the lifecycle — backlog, SPEC, PLAN, TASKS, `_RELEASE.json` and
  `BUGS.jsonl` carry ordered work; no runtime drives agents through steps.
- Deterministic boundaries — path class, bind scope, root hygiene, venv-rooting and
  the git push gate are mechanical, each refusal carrying its own runnable fix.
- Visible concurrency — sessions may race, git exposes the overlap, and nothing
  freezes waiting on a lock.
- No mechanism without a demand, and no slop: runtime state, reports, handoffs,
  caches and projections have canonical homes and never leak into a repository.
- Success is evidenced by reviews, task markers, commands and artifacts, never
  inferred from prose.

## Two ways in

<!-- derived-from: product-vision sha256:89dc2ce6898d -->

A human installs it from PyPI and drives it from a shell: `dadaia init <dir> --harness <name> --repo <url>`
provisions a workspace with its first project ALIVE and bound in one line, and
`dadaia doctor` lists findings with a runnable fix under every refusal.

An agent reads the root `AGENTS.md` map — flow, roles, gate invariants, where things
live, the index of every scoped law and skill — then opens the scoped `AGENTS.md` of
the area it works in; `llms.txt` at the repository root is its index.

Claude Code, Codex, Kimi Code, Cursor, Devin and GitHub Copilot are the entry
harnesses. There is one authored set of law and skills; every harness view of it is a
view, not a copy.
