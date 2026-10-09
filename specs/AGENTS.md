# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.

- Every path here is MUTATING, `memory/` included; how a write lands: the root `AGENTS.md` map §3.

## 1. Canon and status

- `Approved`, `In review`, `Draft` are the canonical status tokens — keep them as-is, in any language; `release.py phase` matches `**Status:** Approved` literally.
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

## 2. Load order

- Ground the session with `dd-spec-navigator` — context, memory bootstrap, live release state, then the current candidate's SPEC, PLAN and job files.
- `_archive/` and `backlog/` are history and intake; neither is an approval.

## 3. Before implementing

- The live release's `_RELEASE.json` `phase` reads `IMPLEMENTATION`: `release.py phase` enters it only when the candidate's SPEC and PLAN both carry `**Status:** Approved`.
- The task is a row of its job file (`rc-<N>/tasks/job<n>.md`), and its declared write set names every file touched.
- Any item missing: stop and emit the §7 `[SDD BLOCKED]` block naming it. A hotfix job needs only its open bug (`specs/bugs/AGENTS.md` §2).

## 4. Artifact authority

| Path | Writer |
|---|---|
| `constitution.md` | operator, or `dd-product-engineer` under approved governance work |
| `releases/<id>/_RELEASE.json` | `python3 .agents/skills/dd-release-implementation/scripts/release.py new\|phase\|memory\|ship`; `log` entries per `dd-release-implementation`'s `RELEASE-EVENTS.md` table |
| `releases/<id>/rc-<N>/{SPEC,PLAN}.md`, `rc-<N>/tasks/job<n>.md` (read-only after its closure; archived whole at promote) | `dd-product-engineer` (SPEC), `dd-software-engineer` (PLAN, job files) |
| `memory/**` | `dd-product-engineer`; phases and tiers: `memory/AGENTS.md` §1 |
| `backlog/**` | `dd-product-engineer`; entries exit by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit` |
| `bugs/**` | any agent, by verbs only; propose and confirm: `bugs/AGENTS.md` |
| `audits/**` | the main thread, from the reviewer's audit-lens report; how a finding moves: `audits/AGENTS.md` |

## 7. Escalation

```text
[SDD BLOCKED]
Context: <context>
Release: <release-id>
Artifact: <path>
Reason: <one sentence>
Needed decision: <one concrete question or action>
```

Project teams may customize this file; `.dadaia/.venv/bin/dadaia doctor` reports drift instead of overwriting it.
