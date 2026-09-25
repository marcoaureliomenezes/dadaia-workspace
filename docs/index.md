# dadaia-workspace

A local-first, spec-driven workspace that gives AI agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.

Start here:

- [Quickstart](quickstart.md) — from `pip install` to a bound project, a backlog entry and a live release.
- [Positioning](positioning.md) — why your product repos never carry agent config, and how one law governs many projects.
- [The bug loop](bug-loop.md) — register, RED test, fix, resolve with evidence and lineage.

Reference: [concepts](concepts.md) · [getting started](getting-started.md) · [CLI](cli.md) · [distribution](distribution.md).

Repository: <https://github.com/marcoaureliomenezes/dadaia-workspace>

## What it is

<!-- derived-from: product-vision sha256:2e29564d7512 -->

dadaia-workspace is the operating environment around repositories developed with AI
agents, and its unit is the context.

A workspace is one folder. The agent session launches at its root, always. Projects
live in repos inside it (`repos/<slug>/`) and the governance — the root `AGENTS.md`
map, the scoped `AGENTS.md` files, `.agents/skills`, `.agents/agents`, `.dadaia/` —
lives outside every repo. A project is a context: one main repo, where `specs/` lives,
plus its associated repos. A workspace holds many contexts and a context many repos; it
is never a monorepo, and a single-repo context is the minimal case.

What it rests on:

- Current context — agents bind explicitly and receive only the relevant project,
  memory, release and task state.
- Documents are the lifecycle — backlog, SPEC, PLAN, TASKS, `_RELEASE.json` and
  `BUGS.jsonl` carry ordered work; no runtime drives agents through steps.
- Deterministic boundaries — path class, bind scope, root hygiene, venv-rooting and
  the push gate are mechanical, each refusal carrying its own runnable fix; what
  cannot be mechanical is written as law.
- Visible concurrency — sessions may race, git exposes the overlap, and nothing waits
  on a lock.
- No mechanism without a demand, and no slop: runtime state, reports, handoffs,
  caches, projections and temporary files have canonical homes and never leak into a
  repository.
- Success is evidenced by reviews, task markers, commands and artifacts, never
  inferred from prose.

## Two ways in

<!-- derived-from: product-vision sha256:2e29564d7512 -->

A human drives it from a shell in three levels:
`uvx dadaia-workspace init <dir> --harness <name> --repo <url>` provisions the
workspace and its first project ALIVE (`context bind` binds),
`.dadaia/.venv/bin/dadaia specs init --context <slug>` brings the project's `specs/`
to the canon, the first pass fills memory, `context baseline` publishes it, and
`.dadaia/.venv/bin/dadaia doctor` prints the next step and every finding with a
runnable fix; `.dadaia/.venv/bin/dadaia context create --main-repo <url>` adds the next
project, and re-running the `uvx` init line upgrades the workspace.

An agent reads the root `AGENTS.md` map — flow, roles, gate invariants, where things
live, the index of every scoped law and skill — opens the scoped `AGENTS.md` of its
area, and works inside the gate, the ledger scripts and the handoff contract;
`llms.txt` at the repository root is its index.

Claude Code, Codex, Kimi Code, Cursor, Devin and GitHub Copilot are the entry
harnesses, one registry record each. The same canonical rules reach every harness
through one authored set, read natively or through per-entry symlinks. Both paths read
one truth: every page here derives from a named memory atom under its content hash.
