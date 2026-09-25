---
name: dd-gitflow-default
description: >
  The three-branch contract whenever git is touched: when to start work, which
  branch to cut, how a release rides it, the isolated commit shapes, and what gates
  a push. Use when branching, committing, opening a PR, starting a task, or minting
  a version.
---

# dd-gitflow-default — The Branch Contract

The branch contract by role; the names are `specs/constitution.md`'s `gitflow:` block (`<work>M.m.p` = work prefix + version).

## 1. When

- Start of any session touching git.
- Branching, committing, opening a PR, starting a task, or minting a version.
- Any bug fix (`dd-bug-resolution`).

## 2. Steps

1. `git fetch --all --prune`.
2. Read the gitflow block; diff the principal against the integration branch — a nonzero diff means the integration branch carries undeployed work.
3. Identify the one live work branch `<work>M.m.p`.
4. Surface a work branch predating the integration branch's last move to the operator first — it is stale.
5. Branch count, cut point and name follow §2a.
6. Definition stage: author the candidate's SPEC/PLAN/TASKS at the release root on the work branch.
7. Implementation stage: one commit per completed task group, shaped per §3a.
8. Candidate closure: open one work → integration PR and merge it green.
9. After the merge, ask the operator: **promote or continue?** Continue = the next candidate's `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id>`; promote = step 10.
10. Promote: open the PR integration → principal (ship verdict pre-staged naming the integration tip, §3b); merging it lets release-please open the release PR that carries the version, the CHANGELOG and the tag.
11. The moment the release PR merges, record it — `python3 .agents/skills/dd-release-implementation/scripts/release.py phase CLOSURE --sha <sha> --pr <n>` — then delete the work branch, cut `<work>{next}` from the principal and `git merge -s ours origin/<integration>`, in that order.
12. Tag `archive/<name>` then delete a branch the moment its work lands elsewhere.

## 2a. The branch contract

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| work `<work>M.m.p` | Yes — local CI preflight + valid name | principal | the PR below |
| integration | No — never a direct push | principal (bootstrap only) | PR from the work branch, at definition `Approved` and at each `rc` merge; Dependabot update PRs (`target-branch` = integration) |
| principal | No — never a direct push | — | PR from the integration branch, at the final `rc` |

- No `v` prefix, no suffix, no other branch we cut; the only bot heads are release-please's release PR into the principal and Dependabot's into the integration branch; `hotfix/*` is retired (operator request only, no cadence).
- Exactly one live work branch, named for the live release; bugs fix on it in any phase, no ceremony.
- The release version = `0.1.0` when the repo has no tag, else last tag + 1 patch, minted at birth; it increments ONLY at an operator-approved deploy.
- Each candidate closure burns one work -> integration merge; after it, ask the operator: promote or continue.
- Every flow stage runs on the work branch; the integration and principal branches are PR targets only, never a working branch.

## 3a. Commit shapes — each write alone, in its own shape

| # | Write | Staged set | Message |
|---|---|---|---|
| 1 | Bug registration | `specs/bugs/BUGS.jsonl` alone | `chore(bugs): report <id>` |
| 2 | Backlog / ADR | `BACKLOG.json` alone, or `ADRs/decisions.jsonl` alone | `chore(backlog): …` / `chore(adrs): …` |
| 3 | Bug fix | code + regression test + the `BUGS.jsonl` line, together | `fix(bugs): <id> — <cause>` |
| 4 | Resolve record | commits only; a push happens when asked, `.dadaia/.venv/bin/dadaia ci preflight` first | — |
| 5 | Release definition | SPEC + PLAN + TASKS + the picked entries flipped to `status: picked` + picked bugs, one commit | `feat(specs): define candidate …` |
| 6 | Task implementation | the task's declared write set | `conventional-commit(task-id): description` — the auditable trace |

## 3b. The PR gate

- Both PR edges require CI green (lint, typecheck, tests, doctor, gitleaks) and a
  `dd-code-reviewer` APPROVED verdict, security lens included, on the PR head; no CI job
  calls a model API. The ruleset is the operator's.

## 4. Done when

- Every commit for a release traces to a candidate's definition, implementation,
  closure merge, or a bug fix — each write alone in its §3a shape, verifiable by
  `git log`.

## 5. References

- [`CICD-AUTOMATION.md`](CICD-AUTOMATION.md) — CI/CD checks to suggest a consumer operator.
- Mechanical enforcement (pre-push hook / CI): branch-name pattern, push refusal,
  denylist scan, `pr-source-guard`. Everything else in this skill is discipline, upheld by agents and
  reviewers, unenforced by any hook.
