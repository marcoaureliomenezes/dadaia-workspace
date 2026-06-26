# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.
Root workspace behavior is in the workspace `AGENTS.md`; production-source
behavior is in the repo-local `AGENTS.md`.

## Lifecycle is owned by the dadaia-workflows

The ordered SDD ritual — the load order (read constitution/memory/`ACTIVE.md`/
SPEC/PLAN/TASKS before acting), the release gate (`Aprovado` artifacts +
`phase: IMPLEMENTATION` + reserve the task `[ ]`→`[-]` before production edits +
stay inside the declared write set), and the per-phase definition → implementation →
review → closure sequence — is executed by the **dadaia-workflows** (the
`dadaia lifecycle` verbs), each a Python workflow body with fragment-scoped prompts and
**Python-validated gates**. Agents are **oriented toward** those workflows; the
disk/commit boundary is **safety-gate-enforced** by the deterministic SDD gate and git
chokepoints (write-scope, lease, phase). Open **`dadaia panel` → Agentic →
dadaia-workflows** for each workflow's purpose, ordered steps, per-step harness/model,
mermaid diagram, and availability.

Use `_archive/` only for history. Use `backlog/` and `bugs/` for intake and
triage; they are not approval gates. (`Aprovado`, `Em revisão`, and `Draft` are the
canonical SDD status tokens — do not translate them.)

## Artifact Authority

| Path | Writer |
|---|---|
| `constitution.md` | operator or `product-engineer` during approved governance work |
| `releases/ACTIVE.md` | `product-engineer` |
| `releases/<id>/SPEC.md` | `product-engineer` |
| `releases/<id>/PLAN.md` | `product-engineer` |
| `releases/<id>/TASKS.md` | `product-engineer`; implementers may change only their task marker |
| `releases/<id>/CLOSURE.md` | `product-engineer` in `CLOSURE` |
| `memory/**` | `product-engineer` in `CLOSURE` only |
| `backlog/**` | `product-engineer` or operator intake |
| `bugs/**` | any agent may file; `product-engineer` resolves into release work |

## Task Markers

Use only these markers:

```text
[ ] OPEN
[-] IN PROGRESS
[x] DONE
```

Do not take a task already marked `[-]`. Do not mark `[x]` without validation
evidence in the implementing report.

## Memory

Memory describes the product as it is now.

- No changelog/history/version sections in `memory/**`.
- Screenshots referenced by memory live under `assets/`.
- Stale memory found during implementation becomes a bug or closure note; do
  not patch memory mid-implementation.

## Doctor

Run before closing spec work:

```bash
dadaia specs doctor
```

`dadaia specs doctor --fix` may repair scaffoldable tree issues. It must not be
used to bypass missing approval, unclear scope, or task ownership.

## Escalation

Use this exact shape when blocked:

```text
[SDD BLOCKED]
Context: <context>
Release: <release-id>
Artifact: <path>
Reason: <one sentence>
Needed decision: <one concrete question or action>
```

Generated from `dadaia_workspace/public/templates/specs-AGENTS.md`. Project
teams may customize this file; `dadaia specs doctor` reports drift instead of
overwriting it.
