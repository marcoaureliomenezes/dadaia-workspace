---
name: dd-gitflow-default
description: >
  The three-branch contract whenever git is touched: when to start work, which
  branch to cut, how a release rides it, the isolated commit shapes, and what gates
  a push. Use when branching, committing, opening a PR, starting a task, or minting
  a version.
---

# dd-gitflow-default — The Branch Contract

The branch contract, stated once, and the mechanics that operate it.

## 1. When

- Start of any session touching git.
- Branching, committing, opening a PR, starting a task, or minting a version.
- Any bug fix (`dd-bug-resolution`).

## 2. Steps

1. `git fetch --all --prune`.
2. Diff `main` against `develop` — a nonzero diff means `develop` carries undeployed work.
3. Identify the one live `feature/{M.m.p}` branch.
4. Surface a `feature/{v}` predating `develop`'s last move to the operator first — it is stale.
5. Branch count, cut point and name follow §2a.
6. Definition stage: author the candidate's SPEC/PLAN/TASKS at the release root on `feature/{M.m.p}`.
7. Implementation stage: one commit per completed task group, shaped per §3a.
8. Candidate closure: open one `feature/{M.m.p}` → `develop` PR and merge it green.
9. After the merge, ask the operator: **promote or continue?** Continue = the next candidate's `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id>`; promote = step 10.
10. Promote: open the PR `develop` → `main` (ship verdict pre-staged naming develop's tip, §3b); merging it lets release-please open the release PR that carries the version, the CHANGELOG and the tag.
11. The moment the release PR merges, record it — `python3 .agents/skills/dd-release-implementation/scripts/release.py phase CLOSURE --sha <sha> --pr <n>` — then delete `feature/{M.m.p}`, cut `feature/{next}` from `main` and `git merge -s ours origin/develop`, in that order.
12. Tag `archive/<name>` then delete a branch the moment its work lands elsewhere.

## 2a. The branch contract

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| `feature/{M.m.p}` | Yes — local CI preflight + valid name | `main` | the PR below |
| `develop` | No — never a direct push | `main` (bootstrap only) | PR from `feature/{M.m.p}`, at definition `Approved` and at each `rc` merge; Dependabot update PRs (`target-branch: develop`) |
| `main` | No — never a direct push | — | PR from `develop`, at the final `rc` |

- No `v` prefix, no suffix, no other branch we cut; the only bot heads are release-please's release PR into `main` and Dependabot's into `develop`; `hotfix/*` is retired (operator request only, no cadence).
- Exactly one live `feature/{M.m.p}`, named for the live release; bugs fix on it in any phase, no ceremony.
- The release version = `0.1.0` when the repo has no tag, else last tag + 1 patch, minted at birth; it increments ONLY at an operator-approved deploy.
- Each candidate closure burns one `feature -> develop` merge; after it, ask the operator: promote or continue.
- Every flow stage runs on `feature/{M.m.p}`; `develop` and `main` are PR targets only, never a working branch.

## 3a. Commit shapes — each write alone, in its own shape

| # | Write | Staged set | Message |
|---|---|---|---|
| 1 | Bug registration | `specs/bugs/BUGS.jsonl` alone | `chore(bugs): report <id>` |
| 2 | Backlog / ADR | `BACKLOG.json` alone, or `ADRs/decisions.jsonl` alone | `chore(backlog): …` / `chore(adrs): …` |
| 3 | Bug fix | code + regression test + the `BUGS.jsonl` line, together | `fix(bugs): <id> — <cause>` |
| 4 | Resolve record | commits only; a push happens when asked, `dadaia ci preflight` first | — |
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
