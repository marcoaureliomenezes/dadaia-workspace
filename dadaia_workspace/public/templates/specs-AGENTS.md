# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.
Root workspace behavior is in the workspace `AGENTS.md`; production-source behavior is in the repo-local `AGENTS.md`.

## 1. Canon and status

- `Approved`, `In review`, `Draft` are the canonical status tokens — keep them as-is, in any language.
- The tree holds only these members; `dadaia doctor` flags anything else, and no stray root archive directory or dotfile is canon.

<!-- specs-canon -->

- Path classes: `bugs/`, `backlog/`, `audits/` and each area's `_archive/*_histo.jsonl` are ADDITIVE, always writable; everything else here is MUTATING, `memory/` included.

## 2. Load order

- Ground the session with `dd-spec-navigator` — context, memory bootstrap, live release and its trio, in that order.
- `_archive/` and `backlog/` are history and intake; neither is an approval.

## 3. Before implementing

- The live release's `_RELEASE.json` `phase` reads `IMPLEMENTATION`, and `SPEC.md`/`PLAN.md`/`TASKS.md` all carry `**Status:** Approved`.
- The task is flipped `[ ]` -> `[-]` before any production edit, and its declared write set names every file touched.
- Any item missing: stop and repair the SDD artifact instead of editing production.

## 4. Artifact authority

| Path | Writer |
|---|---|
| `constitution.md` | operator, or `project-manager` under approved governance work |
| `releases/<id>/_RELEASE.json` | `dadaia release phase|new|rc-archive|archive`; `log` entries by the narrating agent |
| `releases/<id>/{SPEC,PLAN,TASKS}.md` | `project-manager` (SPEC), `software-engineer` (PLAN, TASKS); implementers change only their own task marker |
| `memory/**` | `project-manager`, in `DEFINITION` and `CLOSURE` phase |
| `backlog/**` | `project-manager`; entries exit by `dadaia backlog exit` |
| `bugs/**` | any agent, after the operator confirms the proposal; verbs only |
| `audits/**` | `code-reviewer` (audit lens); findings move by `dadaia audit disposition|close` |

## 5. Memory

- Memory describes the product as it is now; no changelog, history or version sections.
- Stale memory found during implementation becomes a bug proposal or a closure note — never patched mid-implementation.

## 6. Bugs

- A bug is fixed on the live `feature/{M.m.p}` branch, in any phase, with no release ceremony.

## 7. Escalation

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
