# dadaia-workspace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/dadaia-workspace)](https://pypi.org/project/dadaia-workspace/)

A local-first, spec-driven workspace that gives AI agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.

A workspace is one folder. You open an agent session at its root. Your projects live in
repos inside it, and the governance — `AGENTS.md`, `.agents/`, `.dadaia/` — sits outside
every repo. One workspace holds many projects and a project many repos; it is never a
monorepo. Each project is a context: its **main repo** is the repo where `specs/` lives,
its **associated repos** are the others it owns.

## What it is and principles

<!-- derived-from: product-vision sha256:16060412dc8a -->

dadaia-workspace is the operating environment around repositories developed with AI
agents. Its unit is the context: one main repo, where `specs/` lives, plus its
associated repos; a single-repo context is the minimal case. Eight pillars:

- **Current context** — agents bind explicitly and receive only the relevant project,
  memory, release and task state.
- **Documents are the lifecycle** — backlog, SPEC, PLAN, TASKS, `_RELEASE.json` and
  `BUGS.jsonl` carry ordered work; no runtime drives agents through steps.
- **Deterministic boundaries** — path class, bind scope, root hygiene, venv-rooting and
  the push gate are mechanical, each refusal carrying its own runnable fix; what cannot
  be mechanical is written as law.
- **Visible concurrency** — sessions may race, git exposes the overlap, and nothing
  waits on a lock.
- **No mechanism without a demand** — a capability exists only while it earns its
  maintenance cost, and deleted surface beats accreted surface.
- **No slop** — runtime state, reports, handoffs, caches, projections and temporary
  files have canonical homes and never leak into repositories.
- **Six entry harnesses** — Claude Code, Codex, Kimi Code, Cursor, Devin and GitHub
  Copilot, one registry record each; public assets originate once, stage once, and are
  read natively or through per-entry symlinks.
- **Evidence, never prose** — success is evidenced by reviews, task markers, commands
  and artifacts.

Two usage paths follow — a human drives it from a shell, an agent reads the root
`AGENTS.md` map — and both read one truth: every section below derives from a named
memory atom under its content hash.

## A human installs and uses it

<!-- derived-from: pypi-distribution sha256:ab76c52ed560 -->
<!-- derived-from: workspace-init sha256:0c2017836e6f -->
<!-- derived-from: context-management sha256:d40d5eeb1115 -->
<!-- derived-from: workspace-doctor sha256:6af42080bf04 -->

```bash
uvx dadaia-workspace init demo --harness claude --repo <clone url>   # level 1 + 2
cd demo
.dadaia/.venv/bin/dadaia specs init --context <slug>                 # level 3
.dadaia/.venv/bin/dadaia doctor --context <slug>   # findings, each with a runnable fix
```

Onboarding has three levels. **Workspace:** `uvx dadaia-workspace init <dir> --harness
<name>` (or `pip install dadaia-workspace`, which installs one CLI under two names,
`dadaia` and `dadaia-workspace`) provisions `.dadaia/.venv`, the `.dadaia/` zones,
`.agents/skills` and the named harness's projection, seeds the state documents without
overwriting them, and (unless `--skip-assets`) stages and installs the public assets —
the one writer of every hook wiring. The wheel ships the full public asset tree, and
`init` resolves the workspace venv's dependencies from PyPI, so it needs network
access. Every later command runs through the workspace's own CLI,
`.dadaia/.venv/bin/dadaia`. **Project:** `--repo <url>` (plus repeatable
`--associated-repo <url>`) clones the repo into `repos/<slug>/`, installs the pre-push
hook, makes the context ALIVE and binds it; a later project is
`.dadaia/.venv/bin/dadaia context create --main-repo <url> [--associated-repo <url>]`.
**Specs:** `.dadaia/.venv/bin/dadaia specs init --context <slug>` brings the repo's
`specs/` to the canon, moving a foreign tree to `specs-bkp/` after consent.

**Upgrade:** re-run the `uvx dadaia-workspace init <dir> --harness <name>` line; it
prints `upgraded A -> B`, or `already at A`.
`.dadaia/.venv/bin/dadaia harness add <name>` adds a harness later.

`.dadaia/.venv/bin/dadaia context bind <ctx>` writes one session record (context,
runtime, pid, `bound_at`) and acquires nothing; `--print-env` emits `DADAIA_CONTEXT`
and `DADAIA_SESSION_ID` for `eval $(…)`. The bind's scope is the context's main repo
plus its associated repos, and it drives the injection of the tech stack and the
memory catalog digest into the session.

`.dadaia/.venv/bin/dadaia doctor` is the one instance validator. Three sections run in fixed order —
`workspace`, `specs`, `ledgers` — each finding one `<CODE> <verdict> <message>` line,
every error-class finding with one `fix: <command>` line and exit 1; there is no score.
`--json` mirrors the run; `--fix` is the reaper: it moves slop to `.dadaia/reaped/`
and deletes only what a TTL expired.

## An agent reads AGENTS.md and uses it

<!-- derived-from: agentic-entities sha256:9f356fd0a4ec -->
<!-- derived-from: sdd-gate-v3 sha256:d3f9d2e93776 -->
<!-- derived-from: release-lifecycle sha256:7d025467878a -->
<!-- derived-from: bug-ledger sha256:9534ded07707 -->
<!-- derived-from: harness-claude-code sha256:266fdf40eaed -->
<!-- derived-from: harness-codex sha256:b907c260a862 -->
<!-- derived-from: harness-kimi-code sha256:4300d3a1724d -->
<!-- derived-from: harness-cursor sha256:480b18aa9b61 -->
<!-- derived-from: harness-devin sha256:ab4a32c4a53d -->
<!-- derived-from: harness-copilot sha256:b93cef868a6f -->
<!-- derived-from: agent-comms sha256:c485c616b2df -->

The always-on law is the root `AGENTS.md` map; every governed area carries its own
scoped `AGENTS.md`, and every `dd-` skill touching an area opens that file first. The
map, the scoped files, `.agents/skills/dd-*` and `.agents/agents/dd-*.md` are authored
once. Codex, Kimi Code, Cursor, Devin and GitHub Copilot read `.agents/skills`
natively; Claude Code reaches skills and personas through per-entry symlinks. A harness
differs only in serialization — event names, hook file, answer shape — and adds no
behaviour.

The gate is one PreToolUse pre-gate: root whitelist, venv guard, SDD gate, in that
order, first block wins; a policy that raises is ALLOW. It blocks exactly three things:
a new workspace-root entry, a `dadaia`/`pip`/`python -m dadaia_workspace` run outside
`.dadaia/.venv/bin/`, and a PROTECTED write or a bound session's MUTATING write into a
`repos/<slug>/` outside its scope. Path classes: ADDITIVE (always writable), MUTATING
(everything else, scope-judged), PROTECTED (session records and the projected law).
Every BLOCK carries exactly one `fix:` line, and a contract test feeds each fix back
through the gate asserting ALLOW. No lease, lock or wait path exists; the gate reads no
`_RELEASE.json`.

Work runs as candidates inside one live release: a picked set, a grill, SPEC, PLAN and
TASKS, one reserved task at a time, `[x]` only after the reviewer's `APPROVED`, then
closure — memory reconciliation, disposition sweep, the `feature -> develop` merge. The
ledger scripts under `.agents/skills/*/scripts/` (`bugs.py`, `backlog.py`,
`release.py`, `audit.py`) are each record's one writer. A bug is proposed to the
operator and registered only after confirmation, then fixed on the live feature branch
with a RED test. Completed work leaves as a `handoff-v1` record, validated by
`.dadaia/.venv/bin/dadaia reports validate`.

## Documentation

<!-- derived-from: pypi-distribution sha256:ab76c52ed560 -->
<!-- derived-from: public-asset-distribution sha256:6e3a34ba5b23 -->

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

<!-- derived-from: pypi-distribution sha256:ab76c52ed560 -->

- GitHub — <https://github.com/marcoaureliomenezes/dadaia-workspace>
- PyPI — <https://pypi.org/project/dadaia-workspace/>
- Agent index — [`llms.txt`](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/llms.txt)
- Changelog — [`CHANGELOG.md`](https://github.com/marcoaureliomenezes/dadaia-workspace/blob/main/CHANGELOG.md)
