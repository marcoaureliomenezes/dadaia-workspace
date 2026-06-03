> **AI agent rules.** This file is generated from
> `dadaia_workspace/public/data/AGENTS.md` by `dadaia public install`.
> Do not put project-specific instructions here. Put them in a scoped
> `AGENTS.md` / `CLAUDE.md` inside the repo or directory they govern.

# dadaia-workspace — Root Rules

You are in a dadaia-workspace SDD workspace. Keep this root file as the global
contract only. More specific rules live closer to the files being edited and
take precedence.

## Operating Defaults

- Language: Portuguese (BR) by default; English is fine for technical terms.
- Tone: direct, concise, operational.
- Use `.dadaia/.venv/bin/python` and `.dadaia/.venv/bin/pip`; do not use system
  Python tooling for workspace commands.
- Temporary files go under `.dadaia/tmp/`, not under `repos/`, `specs/`, or
  `tests/`.
- Public defaults must stay generic: no private repo names, hostnames, IPs,
  customer names, operator-local paths, or optional domain-pack assumptions.

## Repository Hygiene

This repository is the `dadaia-workspace` source library, not a generated
consumer workspace. Never leave generated runtime projections or local harness
files at the repo root.

Forbidden root artefacts:

- `.dadaia/`, `.agents/`, `.claude/`, `.codex/`, `.opencode/`
- `CLAUDE.md`, `opencode.json`, `Makefile`, `playwright.config.ts`
- `playwright-report/`, `test-results/`, coverage/cache directories

Run projection/install smoke tests in a temp workspace under `.dadaia/tmp/` or
pytest `tmp_path`, never against the repository root. If a validation command
must run on the root, remove generated projections before finishing and confirm
`git status --short` contains only intentional source/test changes.

## Scoped Rules

Before editing, check for the nearest scoped rule file:

- `specs/AGENTS.md` governs SDD artifacts, memory, release gates, backlog, bugs.
- `.dadaia/reports/AGENTS.md` governs report files and handoff sidecars.
- `repos/<slug>/AGENTS.md` governs production source for that repo.
- Nested `AGENTS.md` / `CLAUDE.md` files govern their subtree only.

If a scoped file exists, follow it. Do not duplicate its details in root-level
instructions.

## Active Spec Context

Resolve the active Spec Context Project in this order:

1. `DADAIA_CONTEXT=<slug>`
2. `.dadaia/states/primary_context.json`
3. `dadaia context show --json`

If no context resolves, ask the operator to run:

```bash
dadaia context activate <name>
```

For implementation or review, load:

```bash
<specs-dir>/constitution.md
<specs-dir>/memory/architecture.md
<specs-dir>/memory/tech-stack.md
<specs-dir>/memory/product/index.md
<specs-dir>/releases/ACTIVE.md
<specs-dir>/releases/<release-id>/{SPEC,PLAN,TASKS}.md
```

Use `_archive/` only when the operator asks for history.

## SDD Gate

Production edits require an active approved release:

- `ACTIVE.md` points at the release.
- `SPEC.md`, `PLAN.md`, and `TASKS.md` contain `**Status:** Aprovado`.
- The task is reserved in `TASKS.md` with `[-]`.
- The edit stays inside the task's declared write set.

If the gate is missing, stop with:

```text
[SDD HARD STOP]
Cannot proceed without an approved gate.
Missing:
- [ ] SPEC.md/PLAN.md/TASKS.md with **Status:** Aprovado
- [ ] a [-] reservation by the calling agent
What I can do now:
- Draft the missing artifact for operator review
- Refine open questions
- Diagnose without modifying production files
```

Do not edit specs to justify code already written.

## Memory

Memory is current product truth, not history.

- Read memory before changing production behavior.
- Do not write `specs/memory/**` during implementation.
- Only `product-engineer` writes memory, and only during `CLOSURE`.
- Changelog/history belongs in `CLOSURE.md` and `_archive/`.

## Reports and Panel

Every agent report goes under:

```text
.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html
```

Every HTML report must have a sibling `<stem>.handoff.json` sidecar. Validate it:

```bash
dadaia reports validate <path>
```

`dadaia panel` reads context state, reports, servers, workflows, and projection
health. Keep report paths and sidecars machine-readable.

## Lib-Originated Assets

Files listed in `.dadaia/agentic/manifest.json` are generated projections.
Do not edit them in place. Edit the source under `dadaia_workspace/public/`,
then run:

```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

`dadaia public doctor` must include `[ok] public-privacy`.

## Core CLI

```bash
dadaia context show --json
dadaia specs doctor
dadaia public doctor
dadaia server list
dadaia reports validate <path>
dadaia panel
```
