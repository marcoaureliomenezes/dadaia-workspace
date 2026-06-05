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
memory + the pre-push gate). The **structural engine** that physically creates
`alpha-N/rc-N` folders (scaffolder, ACTIVE.md schema, gate path-resolution,
doctor checks, CLI) is **out of scope** and deferred to **v0.1.6** (see §5).

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
Authored under `specs/releases/v0.1.5/adr/`:
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
