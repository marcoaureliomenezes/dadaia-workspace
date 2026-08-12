---
title: "Gitflow standardization — branch law, develop-only push, diff-based security gate, dadaia-gitflow skill"
status: delivered
opened: 2026-08-12
delivered: 2026-08-12
delivered_by: v0.6.0
description: >-
  Operator ruling (2026-08-12): standardize the entire git surface across the
  development cycle. Exactly four branch patterns (main, develop,
  feature/{M.m.p}, hotfix/{M.m.p}); develop is the ONLY pushable branch;
  feature and hotfix branches live local-only; main advances only via PR from
  develop; the push-gate security review is diff-based (origin/develop..develop),
  never a full scan; every lifecycle stage gets an explicit git contract; a new
  public skill dadaia-gitflow carries the whole model; chokepoints enforce it
  mechanically.
intents:
  - subject:
      kind: catalog
      ref: sdd-bug-backlog-governance
    change: >-
      public/data/DADAIA.md —
      Rewrite §5 (Releases) and §6 (Push green) around the four-branch law:
      backlog-definition, research and bug REGISTRATION happen on develop with a
      commit after every registration; release-definition AND
      release-implementation happen on feature/{M.m.p} cut from develop; the
      feature branch merges into local develop at TWO milestones — after the
      definition trio (SPEC/PLAN/TASKS Aprovado) and at ship — and each merge is
      followed by a mandatory diff-based security review and a push of develop;
      bug FIXES happen on hotfix/{M.m.p} (next PATCH), merged to develop, with
      pyproject version bump + CHANGELOG entry at merge and NO release ceremony
      (revokes the PE PATCH>=1-with-SPEC hotfix law); release finalization order
      is memory update -> CLOSURE -> archive; commit/push to main is forbidden
      everywhere (PR from develop only).
  - subject:
      kind: catalog
      ref: public-asset-distribution
    change: >-
      public/skills/dadaia-gitflow/SKILL.md —
      New universal skill: the single home of the branch/commit/push/version
      contract, invoked whenever git is used. Stage-by-stage table
      (backlog-definition, bug-register, bug-fix, release-definition,
      release-implementation, ship, closure/archive) mapping each stage to its
      branch, commit cadence, merge target and push trigger. All other
      skills/agents REFERENCE it, never restate it (ai-context-engineering I4).
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/service.py#push_gate_decision
    change: >-
      Mechanical enforcement in the pre-push gate: refuse any pushed ref that is
      not refs/heads/develop; refuse local branch names outside the four
      patterns; security verdict keyed to the develop diff being pushed
      (origin/develop..develop) instead of the bare per-ref sha match.
      PushRef.local_ref is the natural insertion point (parsed today, unused).
  - subject:
      kind: catalog
      ref: consumer-agent-support
    change: >-
      public/skills + public/agents tier-2 duplicates —
      Update every restatement to defer to dadaia-gitflow: project-orchestration
      (cadence table, feature/{version} mention), dadaia-task-manager,
      dadaia-release-closure, dadaia-release-definition, product-engineer
      (hotfix section rewrite), security-reviewer (scan_target loses 'full' on
      the push gate; diff-only; full scan survives only in the audit lane),
      code-reviewer (PR base = develop->main), project-manager, software-engineer,
      qa-engineer, ai-engineer forbidden-action lists.
  - subject:
      kind: doc
      ref: quality-assurance.md#CI
    change: >-
      .github workflows + branch rules —
      CI job pr-source-guard failing any PR targeting main whose head is not
      develop, then added to main's required checks; develop branch protection
      (done at bootstrap 2026-08-12: no force push, no deletion, enforce_admins);
      retire feature/**+hotfix/v* push triggers (local-only branches).
  - subject:
      kind: doc
      ref: quality-assurance.md#Anti-Slop
    change: >-
      Repo-hygiene fixes found during the line-by-line survey —
      Fix in the same pass: 4 files cite the deleted release-governance rule
      (dadaia-task-manager:54, dadaia-release-closure:121,
      features/specs/doctor_closure_audit.py:286, features/backlog/doctor.py:56);
      5 agents cite constitution §11/§13 that the scaffold template does not
      contain; scaffold/releases/README.md release-dir regex contradicts the
      ^v\d+\.\d+\.\d+$ canon; ai-engineer.md:102/349 stale claim that
      pre-push-ci-gate.sh is the only shell asset in public/scripts/.
---

# Gitflow standardization

## Disposition — DELIVERED — v0.6.0

Consumed in full by release `v0.6.0` (archived at
`specs/_archive/releases/v0.6.0/`). Every intent maps to the FR that delivered it:

| # | Intent subject | Delivered by | Where it lives now |
|---|---|---|---|
| 1 | `sdd-bug-backlog-governance` — `public/data/DADAIA.md` four-branch law | FR1 (T-060-02) | `public/data/DADAIA.md` §5/§6 + its four `0444` projections |
| 2 | `public-asset-distribution` — new universal skill `dadaia-gitflow` | FR2 (T-060-01) | `public/skills/dadaia-gitflow/SKILL.md` (89 lines) |
| 3 | `chokepoints/service.py#push_gate_decision` — mechanical enforcement | FR4 (T-060-04) | develop-only ref policy, four-pattern name validator, develop-diff verdict |
| 4 | `consumer-agent-support` — tier-2 duplicates defer to the skill | FR3 (T-060-03) | 4 skills + 7 agents rewritten as references |
| 5 | `quality-assurance.md#CI` — `pr-source-guard`, branch rules, retired triggers | FR5 (T-060-05, T-060-09) | `.github/workflows/ci.yml` + `main` required checks |
| 6 | `quality-assurance.md#Anti-Slop` — stale citations, regex, false claim | FR6 (T-060-03, T-060-04) | `release-governance` citations, constitution §11/§13, README regex, scripts inventory |

The one item this entry named that was **not** delivered as code is the removal of the
now-dead hotfix-release surface (`dadaia specs hotfix open`, the two `.j2` templates,
SPEC-DOC-023): the release revoked the *law*, and the surface removal is queued as
`specs/backlog/retire-dead-hotfix-surface.md`.

## Description

See frontmatter description. Full decision record: operator Q&A of 2026-08-12
(this session) — serves as the grill record for the consuming release:

1. **Bootstrap**: develop cut from local main (7 commits incl. today's bug
   fixes), pushed after diff-based security APPROVE — done 2026-08-12.
2. **Definition milestone**: feature/{v} merges into develop TWICE (post
   definition-review and at ship), each merge followed by security diff review
   + push of develop.
3. **Hotfix**: mints next PATCH, version bump in pyproject + CHANGELOG at
   merge, NO SPEC/PLAN/TASKS ceremony (bug doctrine preserved: register ->
   fix -> resolved -> commit).
4. **Enforcement**: mechanical — pre-push branch policy + develop-diff security
   verdict + GitHub rules.

## Motivation

The whole branch law today is one unenforced sentence (DADAIA.md §5) stated
twice; there is no develop branch, pushes go from feature branches, and the
security gate accepts full-repo scans. The operator wants git usage
standardized, optimized and mechanically enforced across every stage of the
development cycle, with skills that are clear, objective and direct.

## Acceptance criteria

- The four-branch law is the only pattern the pre-push gate accepts; pushes of
  non-develop refs are refused with an actionable message.
- dadaia-gitflow skill exists, is projected to all harnesses, and every other
  skill/agent references it instead of restating git rules.
- Security push verdict is satisfied by a diff-based review of exactly the
  develop delta being pushed.
- PRs to main from any head other than develop fail a required check.
- The 4 dangling release-governance citations, the constitution §11/§13 gap and
  the scaffold regex contradiction are gone.
- specs doctor + public doctor green; full suite green; CI green on develop.
