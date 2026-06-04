> **AI agent rules.** This file is generated from
> `dadaia_workspace/public/data/AGENTS.md` by `dadaia public install`.
> Do not put project-specific instructions here. Put them in a scoped
> `AGENTS.md` / `CLAUDE.md` inside the repo or directory they govern.

# dadaia-workspace — Root Rules

You are in a dadaia-workspace SDD workspace. Keep this root file as the global
contract only. More specific rules live closer to the files being edited and
take precedence.

## Operating Defaults

- Language: follow the operator's preference; default to English.
- Tone: direct, concise, operational.
- Use `.dadaia/.venv/bin/python` and `.dadaia/.venv/bin/pip`; do not use system
  Python tooling for workspace commands.
- Temporary files go under `.dadaia/tmp/`, not under `repos/`, `specs/`, or
  `tests/`.
- Public defaults must stay generic: no private repo names, hostnames, IPs,
  customer names, operator-local paths, or optional domain-pack assumptions.

## Workspace Root Law

The workspace **root** may contain **only**:

- Directories: `.agents/`, `.claude/`, `.codex/`, `.dadaia/`, `.opencode/`, `repos/`
- File: `AGENTS.md`

**Operator exception:** any file or directory created by the human operator is always
allowed and MUST never be auto-deleted (e.g. `prompt.md`, screenshots). Operator
authorship is determined by human judgment — the hook fails open when origin is ambiguous.

Everything else at root is forbidden. If a legitimate process regenerates an artifact,
it MUST be redirected into a canonical `.dadaia/<subdir>` — never left loose at root.
Agent-generated temp files go to `.dadaia/tmp/<agent>/<YYYYMMDD>/` (see the
`tmp-file-guardrail` rule). Tool caches go under `.dadaia/` (ruff `cache-dir`, coverage
`data_file`, etc.). MCP server working dirs go under `.dadaia/mcps/<server>/`.

This law is enforced deterministically by the `root-whitelist-gate.sh` PreToolUse hook.
Any write that would create a new top-level root entry not in the whitelist above is
**blocked**. The hook reads an optional operator exception list from
`.dadaia/states/root_exceptions.txt` (one glob per line) for documented, deliberate
exceptions (e.g. tool configs that a specific tool hard-requires at root).

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

## Repo cleanliness — no temp/cache/state dirs

No repo — neither the `dadaia-workspace` library repo nor any Spec Context Project repo — may contain tool-generated cache, state, or artifact directories. These dirs are unconditionally forbidden inside any repo working tree:

| Forbidden dir | Origin |
|---|---|
| `.dadaia/` | workspace-level only — lives at the workspace root, NEVER inside a repo |
| `.venv/` | virtual-environment bootstrap artefact |
| `.pytest_cache/` | pytest cache |
| `.mypy_cache/` | mypy incremental cache |
| `.hypothesis/` | hypothesis database |
| `.ruff_cache/` | ruff lint cache |
| `test-results/` | test runner artefact |
| `playwright-report/` | Playwright HTML report artefact |
| `coverage/`, `.coverage` | coverage artefact |

**`.dadaia/` is workspace-level ONLY.** Creating `.dadaia/` inside a repo is a hard violation — it corrupts workspace-vs-repo boundary detection and breaks context resolution for every tool that walks the directory tree.

**Tools must run with caching disabled or redirected outside the repo:**

- pytest: pass `-p no:cacheprovider` (or set `cache_dir` to a path under `.dadaia/tmp/`)
- mypy: set `incremental = false` in config
- hypothesis: set `database = None`
- ruff: pass `--no-cache`
- Playwright: direct `outputDir` and `reporter` to `.dadaia/tmp/<agent>/<date>/`

Ephemeral agent files go to the workspace `.dadaia/tmp/` landing zone (see `tmp-file-guardrail` rule), not into any repo.

Gitignore entries for these dirs are defence-in-depth only. **Gitignore is not a licence to create them.** They must not appear in the working tree at all. CI repo-hygiene checks enforce this.

## Scoped Rules

Before editing, check for the nearest scoped rule file:

- `specs/AGENTS.md` governs SDD artifacts, memory, release gates, backlog, bugs.
- `.dadaia/reports/AGENTS.md` governs human-readable report files.
- `.dadaia/handoff/AGENTS.md` governs machine-readable agent handoff files.
- `repos/<slug>/AGENTS.md` governs production source for that repo.
- Nested `AGENTS.md` / `CLAUDE.md` files govern their subtree only.

If a scoped file exists, follow it. Do not duplicate its details in root-level
instructions.

## Active Spec Context

See `workspace-protocol` rule for the full context-resolution and spec-loading procedure.

## SDD Gate

Production edits require an active approved release:

- `ACTIVE.md` points at the release.
- `SPEC.md`, `PLAN.md`, and `TASKS.md` contain `**Status:** Aprovado`.
  (`Aprovado`, `Em revisão`, and `Draft` are the canonical SDD status tokens — do not translate or change them.)
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

Every HTML report that feeds another agent must have a handoff JSON file under:

```text
.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json
```

Validate it:

```bash
dadaia reports validate <path>
```

`dadaia panel` reads context state, reports, handoffs, servers, workflows, and
projection health. Keep report and handoff paths machine-readable.

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
