# <repo-name> — Repo Context

> This file is loaded by Claude Code, OpenCode, and Codex when working in this repo.
> It complements the workspace-root `AGENTS.md` with repo-domain knowledge.
> Edit this file directly — it is NOT lib-originated and will not be overwritten by `dadaia public install`.

---

## Repo Purpose

<!-- 2-3 sentences: what this repo does and for whom. -->

## Spec Structure

Specs live under `specs/`. Load them in this order before making any change:

1. `specs/constitution.md`
2. `specs/SPEC.md`
3. `specs/features/<affected-feature>/SPEC.md`
4. `specs/z_bug_specs.md` — live unresolved gaps

Approval marker: `**Status:** Aprovado` in the spec header is required before implementation.

## Repo-Specific Stop Conditions

<!-- List behaviors that should halt an agent working in this repo. Examples:
- Editing production files without an approved SPEC + PLAN + TASKS
- Changing a public API without updating specs first
-->

## Key Paths

<!-- List the most important files/directories agents will need to know about. Example:
- `src/` — application source
- `tests/` — test suite (`pytest tests/ -v`)
- `docs/` — documentation
-->

## Key Commands

```bash
# Run tests
# <fill in>

# Lint / format
# <fill in>

# Build / deploy
# <fill in>
```
