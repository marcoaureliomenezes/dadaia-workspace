# dadaia-workspace

A local-first, spec-driven workspace that gives AI agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.

Start here:

- [Quickstart](quickstart.md) — from `uvx` to a bound project, a backlog entry and a live release.
- [Positioning](positioning.md) — why your product repos never carry agent config, and how one law governs many projects.
- [The bug loop](bug-loop.md) — register, RED test, fix, resolve with evidence and lineage.

Reference: [concepts](concepts.md) · [getting started](getting-started.md) · [CLI](cli.md) · [distribution](distribution.md).

Repository: <https://github.com/marcoaureliomenezes/dadaia-workspace>

## What it is

The pillars are listed once, in the [README](../README.md#what-it-is-and-principles).
The unit is the context: one main repo where `specs/` lives, plus its associated repos.

A human reaches a bound project with `uvx dadaia-workspace init <dir> --harness <name> --repo <url>`
and the [quickstart](quickstart.md); `uvx dadaia-workspace init --from <artifact> <dir>`
restores a workspace that `.dadaia/.venv/bin/dadaia export` wrote.

An agent starts at the root map, `dadaia_workspace/public/data/AGENTS.md`, then opens the
scoped law of its area. `llms.txt` at the repository root is its index.
