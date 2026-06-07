# SPEC: v0.1.5 - bug-backlog-release-governance

**Status:** Aprovado
**Release ID:** v0.1.5
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Objective

Close two coupled governance gaps in the dadaia-workspace SDD lifecycle:

1. **Bug/Backlog → Release governance** — define *who* picks bugs and backlog
   items into a release, *how* a bug is guaranteed solved (or subsumed by a more
   complete backlog item), *how* stale bugs/backlog are sanitized, and *that* a
   `dadaia-grill-me` session is mandatory when defining a release.
2. **Release-architecture decision** — record (as ADRs) the move from the
   4-segment anti-pattern (`v0.1.4.1`, `v0.1.4.2`, …) to a `major.minor.patch`
   parent folder that matures through `alpha-N → rc-N` segments, plus the review
   cadence and branch model that go with it.

A third deliverable was added from a v0.1.4 post-mortem (see §3.4): a **mandatory
pre-push CI gate**.

This release delivers the **governance layer** (personas, skills, rules, ADRs,
memory + the pre-push gate) AND — folded in per operator decision 2026-06-05
(ADR-5) — the **structural engine** that physically creates `alpha-N/rc-N`
folders (scaffolder, ACTIVE.md schema v2, gate path-resolution, doctor checks,
CLI). The engine was originally deferred to v0.1.6; it is now in scope for v0.1.5.
Any remaining "v0.1.6"/"deferred" wording below (§4, §5, ADR-1, ADR-2) is
**superseded by ADR-5 and the T-ENG-\* tasks**.

## 2. Context & motivation

- Bugs and backlog already exist as `.md` files under `specs/bugs/` and
  `specs/backlog/` (`dadaia bug new` / `dadaia backlog new`), but there is **no
  rule** governing how they become a release. `bug-fix-fastlane` is even named in
  `project-orchestration` yet never defined.
- The release versioning leaked the 4-segment anti-pattern into
  `specs/releases/`; the v0.1.4 family even produced a **version-ID collision**
  (two different `v0.1.4.3` releases) — the precise failure the new model retires.
- The v0.1.4 family was pushed and marked CLOSED while CI was red (lint, 9 mypy
  errors incl. a latent `json` NameError, stale e2e set). This must never recur.

## 3. Scope (in this release)

All persona/skill/rule files are **lib-originated** — edited at source under
`dadaia_workspace/public/<type>/`, then `dadaia public stage && install`.

### 3.1 Bug/Backlog → Release governance
- **New skill** `dadaia-release-definition` — the protocol product-engineer
  follows: **pick** (dispatched by project-manager) from `specs/bugs/` (open) +
  `specs/backlog/` (candidate/idea); **bug-always-solved** rule (every picked bug
  is fixed in the release **unless** a picked backlog item supersedes it more
  completely — recorded via `superseded_by:` frontmatter on the bug + a SPEC
  note, with the backlog item's TASKS covering the bug's acceptance);
  **sanitize** stale/invalid items (`deferred`/`rejected` + reason, never delete);
  **mandatory `dadaia-grill-me`** when defining a release from bugs+backlog.
- **`product-engineer.md`** — add the release-definition responsibility;
  reconcile the "does NOT discover" line (it discovers *within* bugs+backlog).
- **`project-manager.md`** — add the release-definition dispatch flow (trigger,
  input contract, mandatory-grill gate, segment sequencing).
- **`project-orchestration` skill** — rewrite the Implementation-Review-QA
  contract to the segment/release cadence + branch model (§3.3); define the
  `bug-fix-fastlane` / `release-definition` playbook.
- **`dadaia-grill-me` skill** — add release-definition as a mandatory trigger.
- **Optional rule** `release-governance.md` (always-on, concise).

### 3.2 Release-architecture decision (ADRs only — engine is v0.1.6)
Recorded in §8 (ADR-1..4):
- **ADR-1** — alpha/rc nested model: `v<M>.<m>.<p>/alpha-N/` + `…/rc-N/`, each
  with own SPEC/PLAN/TASKS/CLOSURE; `ACTIVE.md` schema v2 adds a `segment:` field.
  Kills the 4-segment anti-pattern.
- **ADR-2** — hotfix unification: supersede `sdd-hotfix-track`; all releases
  (minor and patch) use the same parent + segment model.
- **ADR-3** — review cadence & branch model (§3.3).
- **ADR-4** — bug/backlog governance (formal record of §3.1).

### 3.3 Review cadence & branch model (locked via grill)
- Single long-lived branch **`feature/{version}`** (e.g. `feature/0.1.5`); alpha
  segments never branch elsewhere.
- **End of each `alpha-N`** → `qa-engineer` **only** → a **commit** on the
  feature branch. No push, no PR, no other reviewers.
- **End of each `rc-N`** → operator chooses:
  - **Ship**: spawn **all three** (`qa-engineer`, `code-reviewer`,
    `security-reviewer`); all `APPROVE` → push `feature/{version}` + open PR →
    merge → CLOSURE → next release.
  - **Iterate**: open `rc-(N+1)`; no trio required.
- This **replaces** the current per-TASK fan-out contract.

### 3.4 Mandatory pre-push CI gate (post-mortem deliverable)
A gate that runs the CI-equivalent suite locally — `ruff format --check`,
`ruff check`, `mypy --strict`, `pytest` — and **blocks `git push`** if any fail.
Wired as a pre-push hook and/or a `dadaia` command. Rationale: the v0.1.4 family
proved locally-solvable failures can reach a push; CI must be the safety net, not
the first line of defense.

## 4. Out of scope (deferred to v0.1.6 — the engine)
Scaffolder for `alpha-N`/`rc-N` folders; `ACTIVE.md` schema-v2 parser
(`segment:`) across gate/navigator/doctor; gate path-resolution to
`releases/<ver>/<segment>/TASKS.md`; doctor nested-segment check (replacing the
flat SemVer SPEC-DOC-016); CLI `dadaia specs release/segment open`; CI
`feature/{version}` branch trigger.

## 5. Bootstrapping note
v0.1.5 is itself authored in the **current FLAT structure**
(`specs/releases/v0.1.5/{SPEC,PLAN,TASKS,CLOSURE}.md` + `adr/`) because the engine
that creates segment folders does not exist yet. The first release to physically
use `alpha-N/rc-N` is the first one created **after** v0.1.6 ships.

## 6. Acceptance criteria
1. `dadaia-release-definition` skill exists and is discoverable; encodes pick /
   bug-always-solved / subsumption / sanitize / mandatory-grill.
2. `product-engineer` + `project-manager` personas reflect the release-definition
   flow; projections verified in `.claude/` AND `.codex/` (manual — doctor does
   not verify persona projection).
3. `project-orchestration` contract reflects the segment/release cadence + branch
   model; `bug-fix-fastlane`/`release-definition` playbook defined.
4. ADR-1..4 authored and `Aprovado`.
5. Pre-push gate blocks a push when any CI-equivalent check fails (demonstrated).
6. `dadaia public doctor` exit 0; `dadaia specs doctor` 0 ERROR; full
   CI-equivalent suite green locally.
7. `git diff` touches only `public/{agents,skills,rules}/`,
   `specs/releases/v0.1.5/**`, the pre-push gate + its wiring, optional CLI + its
   tests, and (CLOSURE) `specs/memory/**`. Scaffolder/gate/ACTIVE schema unchanged.

## 7. References
- Plan: governance design + grill decisions (2026-06-04).
- Memory: `feedback_prepush_ci_gate`, `sdd-hotfix-track` (to be superseded),
  `sdd-release-lifecycle`.
- Backlog sanitization candidate: `specs/releases/v0.1.3` (stale Draft).

---

## 8. Architectural Decision Records

> Recorded inline (the repo's `.gitignore` tracks only SPEC/PLAN/TASKS/CLOSURE
> per release dir; a dedicated ADR location is an SDD-structure change deferred to
> v0.1.6). Each ADR is `Aprovado` for v0.1.5.

### ADR-1 — alpha/rc nested release model
**Decision.** A release is a `major.minor.patch` parent folder maturing through
ordered segments `alpha-1 → … → rc-1 → …`, each with its own SPEC/PLAN/TASKS/
CLOSURE. Always starts at `alpha-1`; may ship from any segment. Naming: parent
keeps `v` prefix, segments hyphenated (`v0.1.5/alpha-1/`, `v0.1.5/rc-1/`).
`ACTIVE.md` gains a `segment:` field (schema v2). **Engine (scaffolder, gate
path-resolution, doctor nested-segment check, CLI) is deferred to v0.1.6**; v0.1.5
is authored flat. Consequence: maturity is first-class and the 4-segment
collision class (two `v0.1.4.3`) is eliminated; the engine is real work for v0.1.6.

### ADR-2 — hotfix unification
**Decision.** Unify all releases (feature and hotfix) under the ADR-1 parent +
segment model. A hotfix is a release that usually ships at `alpha-1`. The flat
`sdd-hotfix-track` is superseded (memory atom annotated, not deleted); the
bug→hotfix origin discipline folds into ADR-4. Mechanical reconciliation of
`dadaia specs hotfix open` + SPEC-DOC-016 happens in v0.1.6. Consequence: one
model/toolchain; archived `v0.1.4.x` folders keep emitting SemVer WARNINGs until
SPEC-DOC-016 is replaced.

### ADR-3 — review cadence & branch model
**Decision.** One long-lived `feature/{version}` branch per release. End of each
`alpha-N` → `qa-engineer` only → commit (no push/PR/other reviewers). End of each
`rc-N` → operator chooses **ship** (spawn qa + code + security; all APPROVE →
push + PR → merge → CLOSURE) or **iterate** (open `rc-(N+1)`). Replaces the
per-TASK reviewer fan-out (per-task implementer discipline unchanged). Consequence:
review effort scales with maturity; the pre-push CI gate (T-GATE-01) + qa-per-alpha
mitigate late code/security review.

### ADR-4 — bug/backlog → release governance
**Decision.** `product-engineer` picks bugs+backlog (dispatched by
`project-manager`). Every picked **bug must be solved** in the release unless a
picked backlog item supersedes it (recorded `superseded_by: <slug>` + SPEC note,
backlog TASKS cover the bug's acceptance). Stale/invalid items are **sanitized**
(`deferred`/`rejected` + reason, never deleted). A `dadaia-grill-me` session is
**mandatory** when defining a release from bugs+backlog. Consequence: bugs can't
be lost; backlog stays sanitized; releases start from refined understanding.
Implemented by T-GOV-01..05.

### ADR-5 — fold the alpha/rc engine into v0.1.5
**Date:** 2026-06-05 · **Deciders:** operator, software-architect, product-engineer
**Decision.** The structural engine that ADR-1/ADR-2 deferred to v0.1.6 is **folded
into v0.1.5**. Rationale: v0.1.5 is unshipped on `feature/0.1.5`; building the
engine in the same release avoids stacking a separate v0.1.6 branch on top of
unmerged governance, and keeps model + mechanics in one coherent release. This
**supersedes** the "engine = v0.1.6 / out of scope" wording in §1, §4, §5, ADR-1,
and ADR-2. The engine is delivered by **T-ENG-01..09**:
- **T-ENG-01** ACTIVE.md schema v2 (`segment:` field) + all readers + tests.
- **T-ENG-02** scaffolder for `alpha-N`/`rc-N` segment folders + tests.
- **T-ENG-03** CLI `dadaia specs release open` + `segment open` + tests.
- **T-ENG-04** `sdd-spec-gate.sh` path-resolution to `releases/<ver>/<segment>/TASKS.md` + gate tests.
- **T-ENG-05** doctor: segment-aware SPEC-DOC-004 + replace flat SemVer SPEC-DOC-016 with a segment check + tests.
- **T-ENG-06** `.gitignore`: track `alpha-*/rc-*` segment SPEC/PLAN/TASKS/CLOSURE.
- **T-ENG-07** hotfix reconciliation (ADR-2): unify `dadaia specs hotfix open` + supersede the flat track.
- **T-ENG-08** CI `feature/{version}` branch trigger + branch-name validation.
- **T-ENG-09** navigator/closure/task-manager/spec-reviewer skill docs updated for segments.

**Consequence.** v0.1.5 grows from "govern now" to "govern + build the engine".
The first release to physically use `alpha-N/rc-N` is the first one created with
the new CLI after v0.1.5 ships (v0.1.5 itself remains authored flat — bootstrap).
