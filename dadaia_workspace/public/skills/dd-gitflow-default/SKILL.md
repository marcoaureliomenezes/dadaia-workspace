---
name: dd-gitflow-default
description: >
  The three-branch contract whenever git is touched: when to start work, which
  branch to cut, how a release rides it, the isolated commit shapes, and what gates
  a push. Use when branching, committing, opening a PR, starting a task, or minting
  a version.
---

# dd-gitflow-default — The Branch Contract

`DADAIA.md` §4 states the law once; this skill is where it operates.

## 1. When

- Start of any session touching git.
- Branching, committing, opening a PR, starting a task, or minting a version.
- Any bug fix (fixed on the live feature branch, in any phase, no ceremony).

## 2. Steps

1. `git fetch --all --prune`.
2. Diff `main` against `develop` — a nonzero diff means `develop` carries undeployed work.
3. Identify the one live `feature/{M.m.p}` branch.
4. Surface a `feature/{v}` predating `develop`'s last move to the operator first — it is stale.
5. Refuse to create a second `feature/*` branch while one is already live.
6. Cut `feature/{next-version}` from `main` only, once `{version}` is deployed on `main`.
7. Name the new branch exactly `M.m.p` — no `v` prefix, no suffix.
8. Definition stage: author the candidate's SPEC/PLAN/TASKS at the release root on `feature/{M.m.p}`.
9. Implementation stage: one commit per completed task group, shaped per §3a.
10. Candidate closure (memory → CLOSURE): open one `feature/{M.m.p}` → `develop` PR and merge it green.
11. After the merge, ask the operator: **promote or continue?** Continue = `dadaia release rc-archive` (trio → `rc-N/`, fresh trio at root, same version, same branch); promote = step 12.
12. Promote: open the PR `develop` → `main` (ship verdict pre-staged naming develop's tip, §3b).
13. The moment it merges, delete `feature/{M.m.p}` and cut `feature/{next}` (step 6) in the same step.
14. Tag `archive/<name>` then delete a branch the moment its work lands elsewhere.

## 3a. Commit shapes — each write alone, in its own shape

| # | Write | Staged set | Message |
|---|---|---|---|
| 1 | Bug registration | `specs/bugs/BUGS.jsonl` alone | `chore(bugs): report <id>` |
| 2 | Backlog / ADR | `BACKLOG.json` alone, or `ADRs/decisions.jsonl` alone | `chore(backlog): …` / `chore(adrs): …` |
| 3 | Bug fix | code + regression test + the `BUGS.jsonl` line, together | `fix(bugs): <id> — <cause>` |
| 4 | Resolve record | commits only; a push happens when asked, `dadaia ci preflight` first | — |
| 5 | Release definition | SPEC + PLAN + TASKS + purge-on-pick + picked bugs, one commit | `feat(specs): define candidate …` |
| 6 | Task implementation | the task's declared write set | `conventional-commit(task-id): description` — the auditable trace |

## 3b. The ship-PR verdict

- Stage the verdict naming develop's CURRENT tip as the last commit on
  `feature/{M.m.p}`, before the final `feature` → `develop` merge — the merged tip's
  first parent is then the named sha.
- Nothing else lands on `develop` between that staged verdict commit and the merge.
- The verdict store is two-hop: PR head, or the head's first parent
  (`features/chokepoints/verdict.py::covering_verdict`).
- The ship PR's verdict is consumed and deleted after the `main` merge, like any
  other.

## 4. Done when

- Exactly one live `feature/*` branch exists at all times, named for the next version
  immediately after each deploy.
- Every commit for a release traces to a candidate's definition, implementation,
  closure merge, or a bug fix — each write alone in its §3a shape, verifiable by
  `git log`.
- Only `feature/*` is pushable directly; `develop`/`main` advance by PR only.

## 5. References

- `DADAIA.md` §4 — the branch-contract law this skill operates.
- [`CICD-AUTOMATION.md`](CICD-AUTOMATION.md) — CI/CD checks to suggest a consumer operator.
- Mechanical enforcement (pre-push hook / CI): branch-name pattern, push refusal,
  denylist scan, `pr-source-guard`, verdict-gate job requiring an APPROVED security
  handoff. Everything else in this skill is discipline, upheld by agents and
  reviewers, unenforced by any hook.
