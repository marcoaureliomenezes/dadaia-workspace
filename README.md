# dadaia-workspace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/dadaia-workspace)](https://pypi.org/project/dadaia-workspace/)

A local-first, spec-driven workspace that gives AI agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.

A workspace is one folder, and your projects live in repos inside it. Governance sits
outside every repo; a project is a context, with one main repo where `specs/` lives and
its associated repos. It is never a monorepo. The folder rules are the root map,
`dadaia_workspace/public/data/AGENTS.md`.

## What it is and principles

dadaia-workspace is the operating environment around repositories developed with AI
agents. Its unit is the context: one main repo, where `specs/` lives, plus its
associated repos; a single-repo context is the minimal case. Eight pillars:

- **Current context** — agents bind explicitly and receive only the relevant project,
  memory, release and task state.
- **Documents are the lifecycle** — backlog, SPEC, PLAN, the job files, `_RELEASE.json` and
  `BUGS.jsonl` carry ordered work; no runtime drives agents through steps.
- **Deterministic boundaries** — path class, bind scope, root hygiene, the verdict
  writer and the push gate are mechanical, each refusal carrying one fix line; what cannot
  be mechanical is written as law.
- **Visible concurrency** — sessions may race, git exposes the overlap, and nothing
  waits on a lock.
- **Features preserve futures** — features and fixes spend options when coupling grows;
  delivery alternates with deletion, simplification or decoupling, and a capability
  exists only while it earns its maintenance cost.
- **No slop** — runtime state, reports, handoffs, caches, projections and temporary
  files have canonical homes and never leak into repositories.
- **Six entry harnesses** — Claude Code, Codex, Kimi Code, Cursor, Devin and GitHub
  Copilot, one registry record each; public assets originate once, and installation
  refreshes staging before native or projected consumption.
- **Evidence, never prose** — success is evidenced by reviews, task commits, commands
  and artifacts.

## A human installs and uses it

```bash
uvx dadaia-workspace init demo --harness claude --repo <clone url>   # level 1 + 2
cd demo
.dadaia/.venv/bin/dadaia specs init --context <slug>                 # level 3
.dadaia/.venv/bin/dadaia doctor --context <slug>   # findings, each with one fix line
```

The three onboarding levels are: the workspace (`uvx dadaia-workspace init <dir> --harness <name>`,
or `pip install dadaia-workspace`, which installs one CLI under two names, `dadaia` and
`dadaia-workspace`); a project (`--repo <url>`, with repeatable `--associated-repo <url>`;
a later one through `.dadaia/.venv/bin/dadaia context create --main-repo <url>`); and the
specs (`.dadaia/.venv/bin/dadaia specs init --context <slug>`, the first memory pass, then
`.dadaia/.venv/bin/dadaia context baseline <slug>`). Their order is the heading
*Onboarding — three levels* of `dadaia_workspace/public/data/AGENTS.md`; `doctor` prints each
next step with its `fix:` line. `.dadaia/.venv/bin/dadaia context bind <ctx>` binds a session;
its scope is the heading *Context, scope and races* of `dadaia_workspace/public/data/dadaia-AGENTS.md`.

**Upgrade:** re-run the `uvx dadaia-workspace init <dir> --harness <name>` line, then
`.dadaia/.venv/bin/dadaia specs init --context <ctx>`. `.dadaia/.venv/bin/dadaia harness add <name>`
adds a harness later.

**Move:** `.dadaia/.venv/bin/dadaia export` writes the contexts and harnesses to
`.dadaia/dist/spec-contexts.json`; `uvx dadaia-workspace init <dir> --from <artifact>` replicates it.

## An agent reads AGENTS.md and uses it

Fast path for multi-agent, spec-driven development: `uvx dadaia-workspace init <dir> --harness <name>` installs the workspace for Claude Code,
Codex, Kimi Code, Cursor, Devin or GitHub Copilot, with its agent skills under `.agents/skills`.
Read the root `AGENTS.md` map, then run `.dadaia/.venv/bin/dadaia doctor`.

Model-readable indexes: `llms.txt` lists the pages, and `llms-full.txt` holds their full text.

The gate is one PreToolUse pre-gate: root whitelist, then SDD gate. Its rules are the root
map's heading *What is enforced*. The always-on law is the root map, `dadaia_workspace/public/data/AGENTS.md`; each governed
area carries its own scoped `AGENTS.md`, listed under its heading *Scoped law — open before
acting there*. A harness differs only in serialization; its deltas are in
`dadaia_workspace/public/skills/dd-ai-eng-knowhow/CLAUDE-CODE.md` and `CODEX.md`. Completed
work leaves as a `handoff-v1` record, validated by `.dadaia/.venv/bin/dadaia reports validate`.

## Documentation

The documentation is the repository's [docs folder](https://github.com/marcoaureliomenezes/dadaia-workspace/tree/main/docs):

- [Quickstart](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/docs/quickstart.md) — install to a bound project, a backlog entry and a
  live release; [positioning](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/docs/positioning.md) — why product repos carry no agent
  config.
- [The bug loop](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/docs/bug-loop.md) — register, RED, fix, resolve;
  [what the bug ledger taught](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/docs/bug-ledger-lessons.md) — measuring the ledger and
  the fix-chain lesson.
- [CLI reference](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/docs/cli.md) · [concepts](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/docs/concepts.md) ·
  [getting started](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/docs/getting-started.md) · [distribution](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/docs/distribution.md)

## Links

- GitHub — <https://github.com/marcoaureliomenezes/dadaia-workspace>
- PyPI — <https://pypi.org/project/dadaia-workspace/>
- Agent index — [`llms.txt`](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/llms.txt)
- Changelog — [`CHANGELOG.md`](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/CHANGELOG.md)
