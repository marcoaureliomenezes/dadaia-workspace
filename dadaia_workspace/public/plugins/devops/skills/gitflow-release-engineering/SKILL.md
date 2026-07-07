---
name: gitflow-release-engineering
description: >
  Use this skill when engineering the branch/release model of a repo — gitflow
  branch discipline, PR/merge gates, semantic versioning and tagging, changelog
  hygiene, and hotfix flow. Carries the branch-topology, release-maturation,
  and PR-gate checklist. Shipped by the devops plugin pack; owned by
  devops-engineer.
---

# Skill: gitflow-release-engineering

The branch-and-release engineering protocol for the `devops` pack. `devops-engineer` uses it
to design and enforce how a repo's changes flow from branch to tagged release. The CI
*pipeline* that executes these gates is the `github-actions-cicd` skill's domain; this skill
owns the branch topology, versioning, and merge discipline the pipeline encodes.

## When to use

- Defining or repairing a repo's branch model (long-lived branches, feature flow, hotfixes).
- Wiring PR/merge gates: required checks, review requirements, protected branches.
- Cutting a release: version bump, tag, changelog, and the ship/iterate decision.
- Designing a hotfix path that does not bypass the gates.

## 1. Branch topology

| Branch | Rule |
|---|---|
| Default (`main`) | Always releasable; receives changes only via gated PR merge — never a direct push. |
| `feature/{version}` / `feature/{slug}` | One branch per release or work item; short-lived; rebased or merged from default deliberately, not drive-by. |
| Hotfix | Branches from the released tag, lands via the same PR gates, and back-merges to the default branch — a hotfix that skips gates is an incident, not a shortcut. |
| No long-lived divergence | Two permanently diverged branches are two products; converge or split the repo. |

Honour `release-governance` where the workspace defines it: a release matures on a single
`feature/{version}` branch through `alpha-N`/`rc-N` segments, and pushes are gated by the
pre-push chokepoints. Encode that ladder; never author a path around it.

## 2. PR / merge gates

- **Protected default branch:** required status checks (build, tests, lint, typecheck),
  required review approvals, no force-push, no gate bypass for administrators.
- **Green-only merges:** a red or flaky-red check is a blocker, not a "merge anyway" —
  never-push-red applies to merges too.
- **One concern per PR:** scoped, reviewable diffs; a PR that needs "and" in its title is
  usually two PRs.
- **Linear-history choice is deliberate:** squash vs merge-commit is a repo-level policy,
  documented once and applied uniformly — not per-PR taste.
- **Stacked changes:** land in dependency order; a stacked PR merges only after its base.

## 3. Versioning and tagging

| Rule | Detail |
|---|---|
| Semantic versioning | `major.minor.patch`; breaking change ⇒ major, feature ⇒ minor, fix ⇒ patch. |
| Tag = immutable pointer | An annotated tag per release on the exact released sha; never retag or move a published tag — a wrong release gets a new version. |
| Version single-source | One canonical version location (manifest or tag-derived); duplicated version strings drift. |
| Pre-releases | `alpha`/`rc` suffixes for maturation segments; a pre-release tag never becomes the final by mutation. |

## 4. Changelog and release notes

- Conventional-commit messages are the machine source; the changelog is generated or curated
  from them per release, not reconstructed from memory at ship time.
- Release notes state user-facing change, breaking changes with migration steps, and known
  issues. An empty "misc fixes" note is a review finding.

## 5. Ship / iterate decision

- End-of-segment: ship (tag + merge + close) or iterate (next `rc-N`) is an explicit,
  recorded decision by the release owner — never an implicit drift into shipping.
- Post-ship: back-merge or rebase any in-flight branches onto the released state promptly;
  stale bases breed phantom conflicts.

## Guardrails

| Rule | Detail |
|---|---|
| Pipeline vs policy | This skill defines the branch/release policy; the CI jobs enforcing it live in `github-actions-cicd`. |
| No application code | Code under release belongs to `software-engineer` / `frontend-engineer`. |
| No gate bypass | Never author, document, or use a path that skips required checks or reviews — including for hotfixes. |
| Privileged review | Branch-protection and gate changes pair with `security-reviewer`. |
| Handoff | Emit handoff JSON via `dadaia-handoff-emitter` under `.dadaia/handoff/<context>/` after the task. |
