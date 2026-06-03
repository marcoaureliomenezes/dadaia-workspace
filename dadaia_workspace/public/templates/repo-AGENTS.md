# <repo-name> — Repo Rules

Scope: this file governs production-source work inside this repo. Workspace SDD
rules live in the root `AGENTS.md`; spec artifact rules live in `specs/AGENTS.md`.

Edit this file directly for repo-specific behavior. It is not overwritten by
`dadaia public install`.

## Repo Purpose

<!-- 2-3 sentences: what this repo ships, who uses it, and its main runtime. -->

## Source Boundaries

<!-- Replace with the repo's real ownership map. Keep it short. -->

| Path | Owner / rule |
|---|---|
| `src/` | application source |
| `tests/` | automated tests |
| `docs/` | docs |

Do not edit generated files, vendored dependencies, build outputs, secrets, or
environment-specific local config unless this file explicitly allows it.

## SDD Entry Check

Before editing production source:

1. Resolve context with `dadaia context show --json`.
2. Read the active release under `specs/releases/<release-id>/`.
3. Confirm `SPEC.md`, `PLAN.md`, and `TASKS.md` are approved.
4. Confirm your task is marked `[-]`.
5. Confirm every edited file is in the task write set.

If any item fails, stop and report the exact missing artifact or task marker.

## Repo Commands

Fill these in during onboarding:

```bash
# install dependencies

# run tests

# lint / format

# build
```

Agents should prefer these commands over guessing toolchains.

## Validation Evidence

Every implementation report must include:

- commands run
- pass/fail output
- changed production paths
- known risk or `none`

Write reports under `.dadaia/reports/<context>/<agent>/` and follow
`.dadaia/reports/AGENTS.md`.

## Stop Conditions

Stop before editing when:

- the active SDD gate is missing or not approved
- the requested change is outside this repo's source boundaries
- the change needs a new public API/behavior not described by SPEC
- tests cannot be run and no alternative validation is available
- a secret, credential, private hostname, or private IP would be committed
