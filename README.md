# dadaia-workspace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/dadaia-workspace)](https://pypi.org/project/dadaia-workspace/)

A local-first, spec-driven workspace that gives AI agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.

A workspace is one folder. You open an agent session there. Your projects live in repos
inside it, and the governance — `AGENTS.md`, `.agents/`, `.dadaia/` — sits outside every
repo, above them all. One workspace holds many projects and many repos; it is never a
monorepo. Each project is a context: its **main repo** is the repo where `specs/` lives,
its **associated repos** are the others it owns.

## What it is and principles

<!-- derived-from: product-vision sha256:89dc2ce6898d -->

dadaia-workspace is the operating environment around repositories developed with AI
agents. Its unit is the context — a Spec Context Project: one registered `specs/`
tree and the repositories it owns. Nine pillars:

- **Current context** — agents bind explicitly and receive only the relevant project,
  memory, release and task state.
- **Documents are the lifecycle** — backlog, SPEC, PLAN, TASKS, `_RELEASE.json` and the
  bug record store carry ordered work; the workspace ships no runtime driving agents
  through steps.
- **Deterministic boundaries** — path class, bind scope, root hygiene, venv-rooting and
  the git push gate are mechanical, each refusal carrying its own runnable fix.
- **Law where mechanism cannot reach** — what cannot be enforced is written once, in
  the root `AGENTS.md` map or in the scoped `AGENTS.md` that owns the area.
- **Visible concurrency** — sessions may race; git exposes the overlap, and nothing
  freezes waiting on a lock.
- **No mechanism without a demand** — a capability exists only while it earns its
  maintenance cost, and deleted surface beats accreted surface.
- **No slop** — runtime state, reports, handoffs, caches, projections and temporary
  files have canonical homes and never leak into repositories.
- **Six Layer-1 entry harnesses** — Claude Code, Codex, Kimi Code, Cursor, Devin, Copilot, one registry record each; public assets
  originate once, stage once, and the authored set is read natively or through
  per-entry symlinks.
- **Evidence, never prose** — success is evidenced by reviews, task markers, commands
  and artifacts.

Two usage paths follow — a human drives it from a shell, an agent reads the root
`AGENTS.md` — and both read one truth: every section below derives from a named memory
atom under its content hash.

## A human installs and uses it

<!-- derived-from: pypi-distribution sha256:7e18d9868790 -->
<!-- derived-from: workspace-init sha256:871519580ea1 -->
<!-- derived-from: context-management sha256:160b285ee271 -->
<!-- derived-from: workspace-doctor sha256:c0ef9b213b31 -->

```bash
pip install dadaia-workspace
dadaia init demo --harness claude --repo <clone url>   # workspace + first project
cd demo && eval $(dadaia context bind <ctx> --print-env)
dadaia doctor --context <ctx>     # compliance before any implementation write
```

`pip install dadaia-workspace` installs the library and its `dadaia` CLI; the wheel
ships the full public asset tree, so `init` works offline from a bare install.

`dadaia init <dir> --harness <name> [--repo <url>] [--skip-assets]` is the only verb
that operates on a zero workspace, and re-running it is idempotent. It provisions the
virtualenv, every zone the registry says `init` creates, the shared skills root and
the one chosen harness's directory, seeds the state documents without overwriting them,
and (unless `--skip-assets`) stages and installs the public assets — the one writer of
every hook wiring. With `--repo <url>` it goes one step further and makes that repo the
workspace's first project: cloned into `repos/<slug>/`, registered as a context with
that slug as its main repo, made ALIVE, given the pre-push chokepoint, and bound to the
shell — `init` calls the context lifecycle, it never reimplements it. Without `--repo`
it says where projects live and names the one command that creates the first one.

`dadaia context bind <ctx>` writes one caller-owned session record carrying context,
runtime, pid and bind time. It acquires nothing and requires no live release;
`--print-env` emits the two variables for an `eval $(…)` shell. Binding sets the write
scope: the context's main repo plus its associated repos.

`dadaia doctor` is the one validator. Three sections run in fixed order — `workspace`,
`specs`, `ledgers` — each finding printed as one `<CODE> <verdict> <message>` line with
a mandatory `fix: <command>` under every error; the findings and the exit code are the
whole report. `--json` mirrors the run; `--fix` applies the repairs a rule owns.

The SDD flow is five verbs of discipline, not an engine: **register** a demand in the
backlog, **define** a candidate's SPEC/PLAN/TASKS, **implement** one reserved task at a
time, **review** before the push, **close** the candidate and merge it.

## An agent reads AGENTS.md and uses it

<!-- derived-from: agentic-entities sha256:2ab5fd5308c8 -->
<!-- derived-from: sdd-gate-v3 sha256:1c17b7e34596 -->
<!-- derived-from: sdd-bug-backlog-governance sha256:753748a55aa3 -->
<!-- derived-from: harness-claude-code sha256:23883db47f8c -->
<!-- derived-from: harness-codex sha256:2391531daea2 -->
<!-- derived-from: harness-kimi-code sha256:ec6b118dc6ac -->
<!-- derived-from: harness-cursor sha256:aeb19cebd0e1 -->
<!-- derived-from: harness-devin sha256:93ac9b208971 -->
<!-- derived-from: harness-copilot sha256:47a805e79df0 -->
<!-- derived-from: agent-comms sha256:8434208d28f3 -->

The always-on law is the root `AGENTS.md` map: the flow, the roles, the gate
invariants, where output is written. Every governed area carries its own scoped
`AGENTS.md`, which takes precedence in its subtree; the skills open theirs before
acting. Sessions launch at the workspace root.

Six Layer-1 entry harnesses run the same law and read the same authored set — Claude
Code, Codex, Kimi Code, Cursor, Devin CLI and GitHub Copilot all load `AGENTS.md`
natively; every one but Claude Code reads `.agents/skills` natively, Claude Code reaches
it through per-entry symlinks under `.claude/`. Each harness is one registry record
(directory, persona transcode, hook dialect): `dadaia init <dir> --harness <name>` picks
one, `dadaia harness add <name>` adds another later. No harness gets a mirror, a copy or
an underived core surface.

The gate is a PreToolUse chain of three policies in fixed order — root whitelist, venv
guard, SDD gate — first block wins; a policy that raises is ALLOW. It blocks exactly
three things: a new workspace-root entry, a `dadaia`/`pip`/`python -m dadaia_workspace`
token run outside the workspace virtualenv, and a PROTECTED write or a bound session's
out-of-scope write under another context's repository. Three path classes, no fourth:
ADDITIVE (always writable), MUTATING (everything else, scope-judged), PROTECTED
(session records and the projected `AGENTS.md` set, fail-closed). Every
BLOCK carries exactly one `fix:` line naming one runnable command, and a contract test
feeds each fix back through the gate asserting ALLOW — a refusal whose fix is itself
refused cannot exist. No lease, mutex or wait path exists, and no phase is consulted.

Governance records change only through their verbs: `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append|resolve|…` for one
record per bug, `backlog.py new|exit` for the operator's demand queue,
`release.py new|phase` for the release state document, and
`audit.py disposition|close` for findings. A bug is proposed to the operator first and
registered only after confirmation — an agent never files one on its own judgement.
Completed work leaves a session as a machine-readable handoff under the workspace
runtime tree, validated by `dadaia reports validate`.

## Documentation

<!-- derived-from: pypi-distribution sha256:7e18d9868790 -->
<!-- derived-from: public-asset-distribution sha256:a0f6d60dd1f1 -->

The site is <https://marcoaureliomenezes.github.io/dadaia-workspace/>:

- [Quickstart](docs/quickstart.md) — install to a bound project, a backlog entry and a
  live release; [positioning](docs/positioning.md) — why product repos carry no agent
  config.
- [The bug loop](docs/bug-loop.md) — register, RED, fix, resolve;
  [what the bug ledger taught](docs/bug-ledger-lessons.md) — the counts and the
  fix-chain lesson.
- [CLI reference](docs/cli.md) · [concepts](docs/concepts.md) ·
  [getting started](docs/getting-started.md) · [distribution](docs/distribution.md)

The skills install without a workspace, from their own built repository:
`npx skills add marcoaureliomenezes/dadaia-skills`.

## Links

<!-- derived-from: pypi-distribution sha256:7e18d9868790 -->

- GitHub — <https://github.com/marcoaureliomenezes/dadaia-workspace>
- PyPI — <https://pypi.org/project/dadaia-workspace/>
- Agent index — [`llms.txt`](llms.txt)
- Changelog — [`CHANGELOG.md`](CHANGELOG.md)
