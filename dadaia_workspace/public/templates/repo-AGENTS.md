# <repo-name> — Repo Rules

Scope: this file governs production-source work inside this repo.
Workspace SDD rules live in the root `AGENTS.md`; spec artifact rules live in `specs/AGENTS.md`.

Edit this file directly for repo-specific behavior. It is not overwritten by `.dadaia/.venv/bin/dadaia public install`.

`verify: <one argv command>` (required by every job merge) and `tests: <globs>` (test paths an implementation commit may not touch), each as a line starting at column 0 here; `WT merge` reads them from the work branch.

## 1. Repo purpose

<!-- 2-3 sentences: what this repo ships, who uses it, and its main runtime. -->

## 2. Source boundaries

<!-- Replace with the repo's real ownership map. Keep it short. -->

| Path | Owner / rule |
|---|---|
| `src/` | application source |
| `tests/` | automated tests |
| `docs/` | docs |

- Edit only the paths §2 owns; generated, vendored and build files change through their own tool.

## 3. SDD entry check

Before editing production source: `specs/AGENTS.md` §3.

## 4. Repo commands

Fill these in during onboarding:

```bash
# install dependencies

# run tests

# lint / format

# build
```

- Agents should prefer these commands over guessing toolchains.

## 5. Tree hygiene

- This tree carries source and its own artifacts only — never a nested `.dadaia/`, which corrupts context resolution for every tree-walking tool.
- Tool caches redirect by configuration (the harness env, each tool's own config) into `.dadaia/tmp/`, never by a remembered command flag; a harness without env declares the gap.
- A bare test, lint or typecheck run from this root leaves the tree clean; gitignore is defence in depth, not permission to create them.
- Published assets carry no private repo name, hostname, IP, customer or infrastructure name, operator-local path or secret.

## 6. Source hygiene

- Rules: `specs/memory/ARCHITECTURE.md`, the `slop-code` fixed section.

## 7. Validation evidence

Reports never live in this tree: the root `AGENTS.md` map §4.
