# GRILL — Release v0.6.0 — Gitflow standardization

**Status:** Aprovado
**Release ID:** v0.6.0
**Kind:** grill session record (`dadaia-grill-me`, mandatory pre-SPEC session for a release
defined from the picked backlog set — `DADAIA.md` §5 (Releases))
**Session:** operator Q&A, structured interview conducted in-session, **2026-08-12**
**Interviewer:** product-engineer · **Respondent:** operator (product owner)
**Picked set:** `specs/backlog/gitflow-standardization.md` (single entry, consumed in full)

---

## 0. Why this record exists

`dadaia-grill-me` is a hard precondition of the SPEC when a release is defined from
bugs + backlog. This file **is** that session's record: the questions put to the operator
on 2026-08-12, the answers given, and the resulting decisions. The picked backlog entry
carries the same decision record in its frontmatter and its `## Description` — that entry
was itself authored *from* this interview, and it names this session as the grill record.
The rulings below are reproduced here verbatim in substance and are **binding on the
SPEC**; where SPEC and this record disagree, this record wins and the SPEC is corrected.

**Bootstrap already executed before the SPEC was authored** (the interview's first ruling
was executable immediately and was executed):

- `develop` cut from **local `main` at `acf1beef`** (7 commits, including the same day's
  bug fixes).
- `develop` pushed **after** a diff-based `security-reviewer` APPROVE of exactly that
  delta.
- CI: **all jobs green** on the pushed `develop`.
- GitHub **branch protection active on `develop`**: no force push, no deletion,
  `enforce_admins` on.

So this release is not designing on a blank page: the four-branch topology exists on the
remote already, and the work is to make the written law, the skills, the agents and the
chokepoints say what the operator is already doing.

---

## 1. Phase 0 — inspection (answered without asking the operator)

Every factual question below was resolved by reading the tree, not by asking. Recorded per
the skill's "answered via inspection" rule.

| Finding | Type | Evidence found by inspection |
|---|---|---|
| The entire branch law is **one sentence**, and it is stated twice | `[INCONSISTENCY]` | `public/data/DADAIA.md:180` — "implemented on a single `feature/{version}` branch"; restated in `project-orchestration` cadence text. Nothing else in the tree defines a branch model. |
| No `develop` branch existed; pushes came from feature branches | `[DRIFT spec↔code]` | `.github/workflows/ci.yml:5-9` — push triggers on `hotfix/v*` and `feature/**`; v0.5.0 `CLOSURE.md` ship record pushes `feature/v0.5.0` directly |
| The push gate keys on a **bare per-ref sha match**, not on a diff | `[DRIFT spec↔code]` | `features/chokepoints/service.py:229` `push_gate_decision`; `PushRef.local_ref` is parsed (`:69`) and **never read** — the natural insertion point for a branch policy |
| `security-reviewer` still admits a **full** scan as a push-gate `scan_target` | `[INCONSISTENCY]` | `public/agents/security-reviewer.md` scan-target section |
| 4 files cite a **deleted** `release-governance` rule | `[STALE CITATION]` | `public/skills/dadaia-task-manager/SKILL.md:54`; `public/skills/dadaia-release-closure/SKILL.md:121`; `features/specs/doctor_closure_audit.py:286`; `features/backlog/doctor.py:56` |
| 5 agents cite `constitution §11` / `§13`; the scaffold constitution has **7 unnumbered `##` sections** and no §11/§13 | `[STALE CITATION]` | `public/scaffold/constitution.md` — `## Propósito`, `## Stack`, `## Segurança`, `## Princípios`, `## Qualidade`, `## Workflow (SDD)`, `## Mapa`; citations in `software-engineer.md:268`, `project-manager.md:100`, `qa-engineer.md:69`, `security-reviewer.md:58/113/240`, `code-reviewer.md:57/113/222`, `product-engineer.md`, `project-auditor.md:267` |
| The scaffold release-dir regex contradicts the release-id canon | `[INCONSISTENCY]` | `public/scaffold/releases/README.md:20` says `^[a-z][a-z0-9-]+$`, which **rejects `v0.6.0`** — the canon is `^v\d+\.\d+\.\d+$` |
| `ai-engineer` claims `pre-push-ci-gate.sh` is the only shell asset in `public/scripts/` | `[DRIFT spec↔code]` | `ai-engineer.md:102` and `:349`; the directory holds **5** files, **3** of them shell (`certify-dadaia-workspace.sh`, `pre-commit-presence-gate.sh`, `pre-push-ci-gate.sh`) |
| The hotfix ceremony law is **live and contradicts the operator's bug doctrine** | `[INCONSISTENCY]` | `public/agents/product-engineer.md` "Hotfix release lifecycle": PATCH≥1 release dir + SPEC from `release_hotfix.md.j2` + CLOSURE — while `DADAIA.md` §1 Arm B fixes a bug on the spot with **no** release material |
| A hotfix branch-name CI job already exists and encodes PATCH≥1 | `[ANSWERABLE]` | `ci.yml:403-418` `hotfix-branch-name` — the pattern is already right; what is missing is that it is a *push*-triggered job on a branch that will no longer be pushed |

**Unanswerable by inspection, therefore asked:** the branch topology itself, where each
lifecycle stage runs, the merge cadence, the hotfix version-mint rule, the finalization
order, the scan shape, and how much of it must be mechanical. Those are §2.

---

## 2. The decision record (operator answers, verbatim in substance)

Seven rulings. Each is binding; each maps to at least one FR in `SPEC.md`.

### D1 — Exactly four branch patterns; `develop` is the only pushable branch

> **Q:** Today the law names one branch shape (`feature/{version}`) and the CI pushes from
> it. What is the complete set of branches you want to exist, and which of them may be
> pushed?

**A.** Exactly four patterns, and no fifth:

| Pattern | Lives | Pushable |
|---|---|---|
| `main` | remote + local | **No** — never pushed to directly |
| `develop` | remote + local | **Yes — the only pushable branch** |
| `feature/{M.m.p}` | **local only** | No |
| `hotfix/{M.m.p}` | **local only** | No |

- Committing or pushing directly to `main` is **forbidden everywhere**.
- `main` advances **only via PR from `develop`**, and that is **GitHub-enforced**, not
  merely written down.
- `feature/*` and `hotfix/*` never reach the remote. They are local integration space.

### D2 — Backlog-definition, research and bug **registration** happen on `develop`

> **Q:** Where do the non-release activities run — backlog curation, research, and the
> `reported` bug event?

**A.** On `develop`, directly. **A commit after every registration** — each bug
registration and each backlog entry is committed as it is written, not batched. These are
ADDITIVE paths; they need no feature branch and must never wait for one.

### D3 — Release definition **and** implementation happen on `feature/{M.m.p}`, which merges into `develop` at **two** milestones

> **Q:** Does the feature branch carry only implementation, or the definition too? And
> when does it come back to `develop`?

**A.** Both. `feature/{M.m.p}` is cut **from `develop`** and carries release-definition
(SPEC/PLAN/TASKS) *and* release-implementation. It merges into **local `develop`** at
**two** milestones:

- **(a) definition milestone** — when the definition trio (SPEC + PLAN + TASKS) is
  **`Aprovado`**;
- **(b) ship milestone** — at ship.

**Each merge is followed by two mandatory steps, in this order:**

1. a **diff-based security review of `origin/develop..develop`** — the delta being pushed,
   nothing more;
2. a **push of `develop`**.

So a release is committed and pushed the moment its definition is reviewed — milestone (a)
is the mechanism that discharges "release defined + reviewed = mandatory commit + push"
(D5).

### D4 — Bug fixes on `hotfix/{M.m.p}` = **next PATCH**; version minted at merge; **no release ceremony**

> **Q:** A bug fix is Arm B — on the spot, no release. But `product-engineer` today
> carries a hotfix *release* law with a SPEC template. Which one survives?

**A.** The bug doctrine survives; the ceremony **is revoked**.

- Fixes run on `hotfix/{M.m.p}` where the version is the **next PATCH**.
- At merge to `develop`: **bump the version in `pyproject.toml`** and **write a
  `CHANGELOG.md` entry**. That is where a patch version is minted.
- **No release ceremony**: no SPEC, no PLAN, no TASKS, **no `specs/releases/<id>/`
  directory** for a hotfix.
- This **explicitly revokes** the current `product-engineer` hotfix law (PATCH ≥ 1 with a
  SPEC from `release_hotfix.md.j2`, condensed 7-phase flow, `dadaia specs hotfix open`
  scaffolding).
- The bug doctrine is unchanged and remains the whole process:
  **register → reproduce on the executed path → RED test → root-cause fix → GREEN →
  `resolved` event → commit.**

### D5 — Finalization order, and the commit cadence

> **Q:** In what order does a release finish, and how often is work committed?

**A.**

- Finalization order is **memory update → CLOSURE → archive**. Not CLOSURE-then-memory.
- **A group of completed tasks = a commit.** Not one commit per file; not one commit per
  release.
- **Release defined + reviewed = mandatory commit + push**, discharged via milestone (a)
  of D3.

### D6 — The push-gate security review is **diff-based only**

> **Q:** The security agent may currently declare a `full` scan on the push gate. Keep it?

**A.** No. On the push gate the review is **diff-based only** — exactly
`origin/develop..develop`, never a full scan. **Full scans survive only in the audit
lane** (a `project-auditor` dispatch). A full repo scan on every push is the wrong
instrument at the wrong boundary; it also makes the verdict impossible to key to a
delta.

### D7 — Enforcement is **mechanical**, not documentary

> **Q:** How much of this must be enforced by a machine rather than by agent discipline?

**A.** All of the branch topology. Three mechanisms:

1. **pre-push refuses any pushed ref except `refs/heads/develop`**, and **validates
   branch-name patterns** against the four permitted shapes.
2. **The security verdict keys on the `develop` delta being pushed**, not on a bare per-ref
   sha match.
3. **A GitHub required check — `pr-source-guard` — fails any PR to `main` whose head is
   not `develop`.**

A law that only lives in a Markdown file is the state this release exists to leave.

---

## 3. Synthesis

**Core problem resolved.** The workspace's git usage was one unenforced sentence, stated
twice, drifting from what the operator actually does; it is now a four-branch topology with
a single home, a stage-by-stage contract, and three mechanical enforcement points.

**Post-refinement status:** **Ready for approval** — no open question remains. The picked
entry is consumable in full; nothing in it was deferred by this session.

**Decisions recorded (ADR-equivalent), with their FR:**

| # | Decision | Consumed by |
|---|---|---|
| D1 | Four branch patterns; `develop`-only push; `main` via PR from `develop` | FR1, FR4, FR5 |
| D2 | Backlog/research/bug-registration on `develop`, commit per registration | FR1, FR2 |
| D3 | Definition + implementation on `feature/{M.m.p}`; two merge milestones, each followed by diff security review + push | FR1, FR2, FR3 |
| D4 | Hotfix = next PATCH, version minted at merge, **no release ceremony** (revokes the PE hotfix law) | FR1, FR2, FR3, FR7 |
| D5 | memory → CLOSURE → archive; task-group = commit; defined+reviewed = commit+push | FR1, FR2, FR3 |
| D6 | Push-gate security review is diff-only; full scan only in the audit lane | FR1, FR2, FR3, FR4 |
| D7 | Mechanical enforcement: pre-push ref+name policy, develop-diff-keyed verdict, `pr-source-guard` | FR4, FR5 |

**Hygiene findings folded into the same release** (Phase 0, §1) — they are all citations of
the very governance surface this release rewrites, so fixing them elsewhere would mean
touching the same lines twice: the 4 dangling `release-governance` citations, the
constitution §11/§13 gap across 5 agents, the scaffold release-dir regex contradiction, and
the `ai-engineer` stale shell-asset claim. → FR6.

**No question was left as "it depends."** No factual question was put to the operator.
