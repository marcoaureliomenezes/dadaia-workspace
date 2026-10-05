# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.
Root workspace behavior is in the workspace `AGENTS.md`; production-source behavior is in the repo-local `AGENTS.md`.

## 1. Canon and status

- `Approved`, `In review`, `Draft` are the canonical status tokens — keep them as-is, in any language.
- The tree holds only these members; `.dadaia/.venv/bin/dadaia doctor` flags anything else, and no stray root archive directory or dotfile is canon.

<!-- specs-canon -->

- Every path here is MUTATING, `memory/` included; how a write lands: the root `AGENTS.md` map §3.

## 2. Load order

- Ground the session with `dd-spec-navigator` — context, memory bootstrap, live release and its trio, in that order.
- `_archive/` and `backlog/` are history and intake; neither is an approval.

## 3. Before implementing

- The live release's `_RELEASE.json` `phase` reads `IMPLEMENTATION`, and its SPEC and PLAN carry `**Status:** Approved`.
- The task is a row of its job file (`rc-<N>/tasks/<job>.md`), and its declared write set names every file touched.
- Any item missing: stop and repair the SDD artifact instead of editing production.

## 4. Artifact authority

| Path | Writer |
|---|---|
| `constitution.md` | operator, or `dd-product-engineer` under approved governance work |
| `releases/<id>/_RELEASE.json` | `python3 .agents/skills/dd-release-implementation/scripts/release.py new\|phase`; `log` entries by the narrating agent |
| `releases/<id>/rc-<N>/{SPEC,PLAN}.md`, `rc-<N>/tasks/<job>.md` (never rewritten after its closure; archived whole at promote) | `dd-product-engineer` (SPEC), `dd-software-engineer` (PLAN, job files); a job's close task writes its `done` |
| `memory/**` | `dd-product-engineer`, in `DEFINITION` and `CLOSURE` phase |
| `backlog/**` | `dd-product-engineer`; entries exit by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit` |
| `bugs/**` | any agent, after the operator confirms the proposal; verbs only |
| `audits/**` | `dd-code-reviewer` (audit lens); findings move by `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition|close` |

## 5. Memory

- Memory describes the product as it is now; no changelog, history or version sections.
- Stale memory found during implementation becomes a bug proposal or a closure note — never patched mid-implementation.

## 6. Bugs

- A bug is fixed on the live work branch (the constitution's `gitflow:`), in any phase, with no release ceremony.

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
Project teams may customize this file; `.dadaia/.venv/bin/dadaia doctor` reports drift instead of overwriting it.
