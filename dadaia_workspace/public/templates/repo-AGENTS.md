# <repo-name> — Repo Rules

Scope: this file governs production-source work inside this repo.
Workspace SDD rules live in the root `AGENTS.md`; spec artifact rules live in `specs/AGENTS.md`.

Change this file through a worktree merge, like any repo file; `public install` never overwrites it.

A line `verify: <one argv command>` (required by every job merge) and `tests: <globs>` (test paths an implementation commit may not touch), each as a line starting at column 0 here; `.dadaia/.venv/bin/dadaia worktree merge` reads `verify:` from the merge's base branch and `tests:` from the job's `wt-rc` (`worktrees/AGENTS.md` §2); a line's words split on whitespace, quotes group a word, and backslashes are literal.

## 1. Source boundaries

- Edit only the paths the repo owns; generated, vendored and build files change through their own tool.

## 2. SDD entry check

Before editing production source: `specs/AGENTS.md`, Before implementing.

## 3. Repo commands

Fill these in during onboarding:

```bash
# install dependencies

# run tests

# lint / format

# build
```

- Agents should prefer these commands over guessing toolchains.

## 4. Tree hygiene

- This tree carries source and its own artifacts only — never a nested `.dadaia/`, which corrupts context resolution for every tree-walking tool.
- Tool caches redirect by configuration (the harness env, each tool's own config) into `.dadaia/tmp/`, never by a remembered command flag; a harness without env declares the gap.
- A bare test, lint or typecheck run from this root leaves the tree clean; gitignore is defence in depth, not permission to create them.
- Published assets carry no private repo name, hostname, IP, customer or infrastructure name, operator-local path or secret.

## 5. Source hygiene

- Rules: `specs/memory/ARCHITECTURE.md`, the `slop-code` fixed section.

## 6. Validation evidence

Reports never live in this tree: the root `AGENTS.md` map §4.
