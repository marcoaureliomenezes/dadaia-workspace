> **AI agent rules.** This file is generated from
> `dadaia_workspace/public/data/AGENTS.md` by `dadaia public install`.
> Do not put project-specific instructions here. Put them in a scoped
> `AGENTS.md` / `CLAUDE.md` inside the repo or directory they govern.

# dadaia-workspace — read `DADAIA.md`

The complete always-on law of this workspace lives in **one file**: `DADAIA.md`, at the
workspace root and mirrored byte-identically into each harness directory
(`.claude/rules/`, `.codex/`, `.kimi-code/`). It is the workspace system prompt: the flow
every demand follows, who owns what, what the gate enforces, where output is written,
how specs, tasks and memory work, the quality bar, the library surface, and the
credential boundary.

@DADAIA.md

If your harness did not follow that import, open the file directly:

- from the workspace root — `DADAIA.md`
- from inside a repo (`repos/<slug>/`) — `../../DADAIA.md`

Read it before acting. This file carries no law of its own; it exists so that harnesses
which discover `AGENTS.md` natively still reach the one place the law is written.

## Scoped rules

More specific rules live closer to the files they govern and take precedence there.
Before editing, check for the nearest scoped file: `specs/AGENTS.md`,
`.dadaia/reports/AGENTS.md`, `.dadaia/handoff/AGENTS.md`, `repos/<slug>/AGENTS.md`, and
any nested `AGENTS.md` or `CLAUDE.md`.
