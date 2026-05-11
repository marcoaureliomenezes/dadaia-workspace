# dadaia-workspace — Repo Context

> This file is loaded when working inside the `dadaia-workspace` library repository.
> It complements the workspace-root `AGENTS.md` with lib-domain knowledge.
> Note: this repo is developed inside a dadaia-workspace runtime (bootstrap paradox — the lib governs itself).

---

## Mandatory Spec Review Order

Before touching any file under `specs/` or `dadaia_workspace/public/`, load documents in this order:

1. `specs/constitution.md`
2. `specs/memory/architecture.md`
3. `specs/memory/product.md`
4. `specs/memory/tech-stack.md`
5. `specs/foundation/SPEC.md`
6. `specs/SPEC.md`
7. Every feature spec affected by the change
8. `specs/PLAN.md` and `specs/TASKS.md` if implementation planning is in scope
9. `specs/z_bug_specs.md`

## Owner Document Map

| Owner document | What it owns |
|---|---|
| `specs/memory/architecture.md` | Runtime workspace template, `.dadaia/` semantics, distribution model |
| `specs/memory/product.md` | Product definition, user roles, conceptual model |
| `specs/memory/tech-stack.md` | Toolchain policy, `.dadaia/.venv`, Python execution policy |
| `specs/foundation/SPEC.md` | Implementation architecture, four-layer structure, anti-drift rules |
| `specs/SPEC.md` | Product behavior, top-level CLI contracts |
| `specs/features/*/SPEC.md` | Feature-specific behavior only |
| `specs/PLAN.md` / `specs/TASKS.md` | Derived — must not override owner documents |

Edit the owner document first. Align affected feature specs second. Regenerate PLAN/TASKS last.

## Approval Marker Policy

A canonical artifact is implementation-ready only when its header contains exactly:

```
**Status:** Aprovado
```

If unresolved issues remain, keep the artifact marked `Em revisão` and record gaps in `specs/z_bug_specs.md`. Only mark `Aprovado` after the refinement pass has no unresolved gaps.

## Repo-Specific Stop Conditions

Stop and signal before proceeding if any of these is true:

- Python automation is being attempted outside `.dadaia/.venv` after bootstrap exists
- A temporary artifact is being written outside `.dadaia/tmp/python/` or `.dadaia/tmp/json/`
- A frozen CLI surface (`dadaia` top-level commands) is being changed without an explicit spec update
- A state machine or JSON schema is being changed only in code, without updating `specs/memory/architecture.md`
- A `dadaia_workspace/public/` asset is being edited without running `dadaia public stage && dadaia public install --target all` afterwards

## Public Asset Workflow

Changes to `dadaia_workspace/public/` (rules, skills, commands, agents, scripts, templates) must be propagated:

```bash
dadaia public stage
dadaia public install --target all --force
dadaia public doctor   # verify all [ok]
```

## Key Commands

```bash
# Quality checks (run before committing)
ruff format dadaia_workspace/
ruff check dadaia_workspace/
mypy --strict dadaia_workspace/

# Unit tests
pytest tests/unit/ -v

# Integration
dadaia public stage && dadaia public install --target all --force

# Drift diagnosis
dadaia public doctor
dadaia doctor
```

## Package Structure

```
dadaia_workspace/
  cli/           ← Typer CLI entrypoints (frozen surface)
  features/      ← Business logic per feature
  core/          ← Models, protocols, exceptions (no I/O)
  infrastructure/← Concrete adapters (JSON, filesystem, git)
  public/        ← Canonical source of all agent assets
    rules/       ← 1 rule file: dadaia-workspace-dev-guardrail.md
    skills/      ← 4 universal skills
    commands/    ← 4 commands
    agents/      ← 4 specialized agents
    scripts/     ← Hook scripts (ctx-inject.sh, sdd-spec-gate.sh)
    data/        ← AGENTS.md template + repos.xlsx
    scaffold/    ← Scaffold for new repo specs/
    templates/   ← Per-repo templates (repo-AGENTS.md)
  container.py   ← Composition root
```
