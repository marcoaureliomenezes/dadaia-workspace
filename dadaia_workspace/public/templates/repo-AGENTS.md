# <repo-name> — Repo Rules

Scope: this file governs production-source work inside this repo.
Workspace SDD rules live in the root `AGENTS.md`; spec artifact rules live in `specs/AGENTS.md`.

Edit this file directly for repo-specific behavior. It is not overwritten by `dadaia public install`.

## 1. Repo purpose

<!-- 2-3 sentences: what this repo ships, who uses it, and its main runtime. -->

## 2. Source boundaries

<!-- Replace with the repo's real ownership map. Keep it short. -->

| Path | Owner / rule |
|---|---|
| `src/` | application source |
| `tests/` | automated tests |
| `docs/` | docs |

- Do not edit generated files, vendored dependencies, build outputs, secrets, or environment-specific local config.
- Exception: only when this file explicitly allows it.

## 3. SDD entry check

Before editing production source:

1. Resolve context with `dadaia context show --json`.
2. Read the active release under `specs/releases/<release-id>/`.
3. Confirm `SPEC.md`, `PLAN.md`, and `TASKS.md` are approved.
4. Confirm your task is marked `[-]`.
5. Confirm every edited file is in the task write set.
6. If any item fails, stop and report the exact missing artifact or task marker.

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
- These never appear in the tree: `<!-- repo-excluded -->`.
- Caches redirect by configuration, never by a remembered command flag: `[tool.pytest.ini_options] addopts`, `[tool.ruff] cache-dir`, `[tool.mypy] cache_dir`, hypothesis `database = None`, Playwright `outputDir` into `.dadaia/tmp/`.
- A bare `pytest` / `ruff check` / `mypy --strict` from this root leaves the tree clean; gitignore is defence in depth, not permission to create them.
- Published assets carry no private repo name, hostname, IP, customer or infrastructure name, operator-local path or secret.

## 6. Source hygiene

- A comment explains a non-obvious why only; the what and the history live in git and the ledgers.
- A docstring states the contract in at most 3 lines.
- Code is born with a real caller in the same change.
- A fix replaces the old path, never wraps it.
- Full statements: `specs/memory/ARCHITECTURE.md`, fixed section Slop — code.

## 7. Validation evidence

Every implementation report must include:

- commands run
- pass/fail output
- changed production paths
- known risk or `none`

Write reports under this repo's `reports/<agent>/`.

## 8. Stop conditions

Stop before editing when:

- the active SDD gate is missing or not approved
- the requested change is outside this repo's source boundaries
- the change needs a new public API/behavior not described by SPEC
- tests cannot be run and no alternative validation is available
- a secret, credential, private hostname, or private IP would be committed
