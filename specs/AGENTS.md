# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.
Root workspace behavior is in the workspace `AGENTS.md`; production-source behavior is in the repo-local `AGENTS.md`.

## 1. Canon and status

- `Approved`, `In review`, `Draft` are the canonical status tokens — keep them as-is, in any language.
- The tree holds only these members; `.dadaia/.venv/bin/dadaia doctor` flags anything else, and no stray root archive directory or dotfile is canon.

| Area | Members |
|---|---|
| root | `AGENTS.md constitution.md memory/ releases/ backlog/ bugs/ audits/ ADRs/` |
| `memory/` | `AGENTS.md ARCHITECTURE.md QUALITY.md product/` |
| `memory/product/` | `index.md catalog.json <area>/<slug>.md` |
| `releases/` | `AGENTS.md _archive/ <M.m.p>/` |
| `releases/_archive/` | `releases_histo.jsonl <M.m.p>/**` |
| `releases/<M.m.p>/` | `_RELEASE.json RELEASE.json rc-<N>/` |
| `releases/<M.m.p>/rc-<N>/` | `SPEC.md PLAN.md TASKS.md tasks/<slug>.md` |
| `backlog/` | `AGENTS.md BACKLOG.json _archive/backlog_histo.jsonl` |
| `bugs/` | `AGENTS.md BUGS.jsonl _archive/bugs_histo.jsonl` |
| `audits/` | `AGENTS.md _archive/audits_histo.jsonl <YYYYMMDD-slug>/` |
| `audits/<YYYYMMDD-slug>/` | `AUDIT.md FINDINGS.jsonl` |
| `ADRs/` | `AGENTS.md decisions.jsonl` |

- Every path here is MUTATING, `memory/` included; how a write lands: the root `AGENTS.md` map §3.

## 2. Load order

- Ground the session with `dd-spec-navigator` — context, memory bootstrap, live release and its trio, in that order.
- `_archive/` and `backlog/` are history and intake; neither is an approval.

## 3. Before implementing

- The live release's `_RELEASE.json` `phase` reads `IMPLEMENTATION`: `release.py phase` enters it only when the candidate's SPEC and PLAN both carry `**Status:** Approved`.
- The task is a row of its job file (`rc-<N>/tasks/<job>.md`), and its declared write set names every file touched.
- Any item missing: stop and repair the SDD artifact instead of editing production.

## 4. Artifact authority

| Path | Writer |
|---|---|
| `constitution.md` | operator, or `dd-product-engineer` under approved governance work |
| `releases/<id>/_RELEASE.json` | `python3 .agents/skills/dd-release-implementation/scripts/release.py new\|phase`; `log` entries by the narrating agent |
| `releases/<id>/rc-<N>/{SPEC,PLAN}.md`, `rc-<N>/tasks/<job>.md` (never rewritten after its closure; archived whole at promote) | `dd-product-engineer` (SPEC), `dd-software-engineer` (PLAN, job files); a job's close task writes its `done` |
| `memory/**` | `dd-product-engineer`; phases and tiers: `memory/AGENTS.md` §1 |
| `backlog/**` | `dd-product-engineer`; entries exit by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit` |
| `bugs/**` | any agent, by verbs only; propose and confirm: `bugs/AGENTS.md` |
| `audits/**` | `dd-code-reviewer` (audit lens); how a finding moves: `audits/AGENTS.md` |

## 5. Memory

- Memory describes the product as it is now; no changelog, history or version sections.

## 6. Bugs

- When a bug is fixed: `specs/bugs/AGENTS.md` §2.

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
