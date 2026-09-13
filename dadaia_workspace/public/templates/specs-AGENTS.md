# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.
Root workspace behavior is in the workspace `AGENTS.md`; production-source behavior is in the repo-local `AGENTS.md`.

## 1. Load order

- Ground the session with `dd-spec-navigator` — context, memory bootstrap, live release and its trio, in that order.
- `_archive/` and `backlog/` are history and intake; neither is an approval.

## 2. Before implementing

- The live release's `_RELEASE.json` `phase` reads `IMPLEMENTATION`, and `SPEC.md`/`PLAN.md`/`TASKS.md` all carry `**Status:** Aprovado`.
- The task is flipped `[ ]` -> `[-]` before any production edit, and its declared write set names every file touched.
- Any item missing: stop and repair the SDD artifact instead of editing production.

## 3. Artifact authority

| Path | Writer |
|---|---|
| `constitution.md` | operator, or `product-engineer` under approved governance work |
| `releases/<id>/_RELEASE.json` | `dadaia release phase|new|rc-archive|archive`; `log` entries by the narrating agent |
| `releases/<id>/{SPEC,PLAN,TASKS}.md` | `product-engineer`; implementers change only their own task marker |
| `memory/**` | `product-engineer`, in `DEFINITION` and `CLOSURE` phase |
| `backlog/**` | `project-manager`; entries exit by `dadaia backlog exit` |
| `bugs/**` | any agent, after the operator confirms the proposal; verbs only |
| `audits/**` | `project-auditor`; findings move by `dadaia audit disposition|close` |

## 4. Memory

- Memory describes the product as it is now; no changelog, history or version sections.
- Stale memory found during implementation becomes a bug proposal or a closure note — never patched mid-implementation.

## 5. Bugs

- A bug is fixed on the live `feature/{M.m.p}` branch, in any phase, with no release ceremony.

## 6. Escalation

```text
[SDD BLOCKED]
Context: <context>
Release: <release-id>
Artifact: <path>
Reason: <one sentence>
Needed decision: <one concrete question or action>
```

Generated from `dadaia_workspace/public/templates/specs-AGENTS.md`.
Project teams may customize this file; `dadaia doctor` reports drift instead of overwriting it.
