# 02. AGENTS.md and Scoped Instructions

`AGENTS.md` is Codex's durable instruction file. Codex builds an instruction chain
when a run or TUI session starts: global guidance first, then project guidance
from the repository root down to the current working directory. Later files are
closer to the task and can override earlier guidance.

## Discovery Order

Codex looks in two broad scopes:

| Scope | Typical File | Purpose |
|---|---|---|
| Global | `~/.codex/AGENTS.md` or `AGENTS.override.md` | Personal defaults across repositories |
| Project | `AGENTS.md` or `AGENTS.override.md` from repo root to CWD | Team and directory-specific rules |

At each directory, Codex includes at most one instruction file. It prefers
`AGENTS.override.md`, then `AGENTS.md`, then any configured fallback filenames.
The combined guidance is capped by `project_doc_max_bytes`, so large root files
can crowd out important local rules.

## Directory Scoping

Use the narrowest directory where the rule is true:

| Rule Type | Best Home |
|---|---|
| Workspace-wide operating contract | Workspace root `AGENTS.md` |
| Source-library hygiene | Repository root `AGENTS.md` |
| SDD artifacts and memory rules | `specs/AGENTS.md` |
| Test commands and fixtures | `tests/AGENTS.md` |
| Package-specific conventions | Nested package `AGENTS.md` |

This is how Codex "scopes" rules to strict directories: not through hidden magic,
but through instruction stacking. A closer file appears later in the prompt and
therefore wins when it conflicts with broader guidance.

## What Belongs in AGENTS.md

Use `AGENTS.md` for persistent expectations:

- build, lint, and test commands;
- repository hygiene;
- review expectations;
- path ownership;
- recurring mistakes the agent must stop making;
- instructions that should be true for every task under that directory.

Do not put long procedures, copied docs, or temporary decisions in `AGENTS.md`.
Those belong in skills, specs, or the current prompt.

## dadaia Mapping

In dadaia-workspace:

- Root `AGENTS.md` is the global workspace contract.
- Repo-local `AGENTS.md` protects the `dadaia-workspace` source library from
  runtime projection artifacts.
- `specs/AGENTS.md` governs SPEC/PLAN/TASKS/memory and release gates.
- Generated runtime projections are not edited directly; source lives under
  `dadaia_workspace/public/`.

The important failure mode is root bloat. If the root file tries to teach every
Codex primitive, it burns context on every task and weakens local focus. Use the
Academy for learning material, skills for repeatable work, and `AGENTS.md` for
small durable rules.

## Verification

When instructions look wrong:

1. Ask Codex to list instruction sources it loaded.
2. Start Codex from the target subdirectory and compare the chain.
3. Check for `AGENTS.override.md` in the global or project path.
4. Check whether `project_doc_max_bytes` truncated the combined file.
5. Restart Codex; instruction discovery happens at run/session start.
