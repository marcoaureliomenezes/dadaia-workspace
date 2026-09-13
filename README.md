# dadaia-workspace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/dadaia-workspace)](https://pypi.org/project/dadaia-workspace/)

A local-first, spec-driven workspace that gives AI agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.

## What it is and principles

<!-- derived-from: product-vision sha256:ec1cebce031b -->

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
  one always-on file.
- **Visible concurrency** — sessions may race; presence warnings and git expose the
  overlap, and nothing freezes waiting on a lock.
- **No mechanism without a demand** — a capability exists only while it earns its
  maintenance cost, and deleted surface beats accreted surface.
- **No slop** — runtime state, reports, handoffs, caches, projections and temporary
  files have canonical homes and never leak into repositories.
- **Three Layer-1 entry harnesses** — Claude Code, Codex and Kimi Code; public assets
  originate once, stage once and project to each runtime root.
- **Evidence, never prose** — success is evidenced by reviews, task markers, commands
  and artifacts.

Two usage paths follow — a human drives it from a shell, an agent reads `DADAIA.md` —
and both read one truth: every section below derives from a named memory atom under
its content hash.

## A human installs and uses it

<!-- derived-from: pypi-distribution sha256:80d67bd879ea -->
<!-- derived-from: workspace-init sha256:5b20a0d9dc80 -->
<!-- derived-from: context-management sha256:a66534def71e -->
<!-- derived-from: workspace-doctor sha256:a78256c47540 -->
<!-- derived-from: panel sha256:c55db1d0ad51 -->

```bash
pip install dadaia-workspace
dadaia init                       # provision a workspace where you stand
dadaia context create <ctx> --repo-url <url> && dadaia context alive <ctx>
dadaia context bind <ctx>         # this session's scope
dadaia doctor --context <ctx>     # compliance before any implementation write
dadaia panel                      # the human view, loopback only
```

`pip install dadaia-workspace` installs the library and its `dadaia` CLI; the wheel
ships the full public asset tree, so `init` works offline from a bare install.

`dadaia init [--workspace PATH] [--skip-assets] [--harness <set>]` is the only verb
that operates on a zero workspace, and re-running it is idempotent. It provisions the
virtualenv, every zone the registry says `init` creates, the shared skills root and
the chosen harness directories, seeds the state documents without overwriting them,
and (unless `--skip-assets`) stages and installs the public assets — the one writer of
every hook wiring.

`dadaia context bind <ctx>` writes one caller-owned session record carrying context,
runtime, pid and bind time. It acquires nothing and requires no live release;
`--print-env` emits the two variables for an `eval $(…)` shell. Binding sets the write
scope: the context's main repo plus its associated repos.

`dadaia doctor` is the one validator. Three sections run in fixed order — `workspace`,
`specs`, `ledgers` — each finding printed as one `<CODE> <verdict> <message>` line with
a mandatory `fix: <command>` under every error, each section ending in a compliance
line. `--json` mirrors the run; `--fix` applies the repairs a rule owns.

The SDD flow is five verbs of discipline, not an engine: **register** a demand in the
backlog, **define** a candidate's SPEC/PLAN/TASKS, **implement** one reserved task at a
time, **review** before the push, **close** the candidate and merge it.

## An agent reads DADAIA.md and uses it

<!-- derived-from: agentic-entities sha256:762aef59899f -->
<!-- derived-from: sdd-gate-v3 sha256:6206bc904484 -->
<!-- derived-from: sdd-bug-backlog-governance sha256:bc20d301cfe8 -->
<!-- derived-from: harness-claude-code sha256:0dd461fa1f27 -->
<!-- derived-from: harness-codex sha256:38cdff41eaea -->
<!-- derived-from: harness-kimi-code sha256:622511bee49b -->
<!-- derived-from: agent-comms sha256:e7f9051b11a9 -->

The complete always-on law is one file, `DADAIA.md`, at the workspace root and mirrored
into the Codex and Kimi Code runtime roots; Claude Code reaches it through the import
chain `CLAUDE.md` → `AGENTS.md` → `DADAIA.md`. A scoped `AGENTS.md` governs its own
subtree and takes precedence there.

Three Layer-1 entry harnesses run the same law. Claude Code is the only one with native
sub-agent dispatch and carries the nine-agent roster; Codex reads Starlark `.rules` and
TOML personas; Kimi Code is wired by POSIX hook shims under its own home. Behaviors,
personas, rules and skills are declared harness-agnostically in one registry and then
implemented per harness — no underived core surface.

The gate is a PreToolUse chain of three policies in fixed order — root whitelist, venv
guard, SDD gate — first block wins; a policy that raises is ALLOW. It blocks exactly
three things: a new workspace-root entry, a `dadaia`/`pip`/`python -m dadaia_workspace`
token run outside the workspace virtualenv, and a PROTECTED write or a bound session's
out-of-scope write under another context's repository. Three path classes, no fourth:
ADDITIVE (always writable), MUTATING (everything else, scope-judged, records advisory
presence), PROTECTED (session records and the projected law files, fail-closed). Every
BLOCK carries exactly one `fix:` line naming one runnable command, and a contract test
feeds each fix back through the gate asserting ALLOW — a refusal whose fix is itself
refused cannot exist. No lease, mutex or wait path exists, and no phase is consulted.

Governance records change only through their verbs: `dadaia bugs append|resolve|…` for
one record per bug, `dadaia backlog new|exit` for the operator's demand queue,
`dadaia release new|phase|rc-archive|archive` for the release state document, `dadaia
audit disposition|close` for findings. A bug is proposed to the operator first and
registered only after confirmation — an agent never files one on its own judgement.
Completed work leaves a session as a machine-readable handoff under the workspace
runtime tree, validated by `dadaia reports validate`.

## Links

<!-- derived-from: pypi-distribution sha256:80d67bd879ea -->

- GitHub — <https://github.com/marcoaureliomenezes/dadaia-workspace>
- PyPI — <https://pypi.org/project/dadaia-workspace/>
- Documentation — [`docs/`](docs/): [CLI reference](docs/cli.md)
- Agent index — [`llms.txt`](llms.txt)
- Changelog — [`CHANGELOG.md`](CHANGELOG.md)
