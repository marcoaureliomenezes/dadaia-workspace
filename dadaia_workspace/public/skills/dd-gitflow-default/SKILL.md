---
name: dd-gitflow-default
description: >
  Use whenever git is touched — branching, committing, opening a PR, starting a new task,
  or minting a version. The one operational home of the three-branch model: when to start
  work, which branch to cut, how a release rides it, and what actually gates a push.
  `DADAIA.md` §4 states the law once; this skill is where it operates.
tldr: "feature/{M.m.p} -> develop -> main, PR-only past feature; 5 isolated commit shapes; delete+cut on deploy."
---

# dd-gitflow-default — The Branch Contract, v2

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
8. Definition stage: author SPEC/PLAN/TASKS on `feature/{M.m.p}`.
9. Open the PR to `develop` the moment the trio is `Aprovado`.
10. Implementation stage: one commit per completed task group.
11. Each `rc`: one `feature/{M.m.p}` → `develop` PR merge; scope is fixes/adjustments only, never new backlog.
12. Stage every write per its isolated shape — table in §4.
13. At the final `rc`, open the PR `develop` → `main`.
14. The moment it merges, delete `feature/{M.m.p}` and cut `feature/{next}` (step 6) in the same step.
15. Tag `archive/<name>` then delete a branch the moment its work lands elsewhere.

## 3. Done when

- Exactly one live `feature/*` branch exists at all times.
- That branch is named for the next version immediately after each deploy.
- Every commit for a release traces to definition, implementation, `rc` merge, or bug fix.
- A `git log` scan finds each write in §4 alone in its own commit, matching its message pattern.
- Only `feature/*` is pushable directly; `develop`/`main` advance by PR only.

## 4. References

- `DADAIA.md` §4 — the branch-contract law this skill operates.
- `CICD-AUTOMATION.md` — concrete CI/CD checks to suggest a consumer operator.
- Commit shape 1 — bug registration: `specs/bugs/BUGS.jsonl` alone — `chore(bugs): report <id>`.
- Commit shape 2 — backlog/ADR: `BACKLOG.json` alone, or `ADRs/decisions.jsonl` alone.
- Commit shape 3 — bug fix: code + regression test + `BUGS.jsonl` line together, one commit.
- Commit shape 4 — resolve commits only; a push happens when asked, `dadaia ci preflight` first.
- Commit shape 5 — release definition: SPEC + PLAN + TASKS + purge-on-pick + picked bugs, one commit.
- Commit shape 6 — task implementation: the task's declared write set — `conventional-commit(task-id): description` (the §3 trace; F016, 20260827 audit: the largest commit class, now classified).
- Mechanical enforcement (pre-push hook / CI job): branch-name pattern, push refusal, denylist scan, CI trigger.
- Mechanical enforcement (continued): `pr-source-guard`, verdict-gate job requiring an APPROVED security handoff.
- Discipline (this skill + reviewers, unenforced by any hook): start-of-work protocol, one-live-branch, delete+cut-on-deploy.
- Verdict store is two-hop: PR head, or head's first parent (`features/chokepoints/verdict.py::covering_verdict`).
- Ship PR (`develop` → `main`): stage the verdict naming develop's current tip as the last commit on `feature/{M.m.p}`, before the final `feature` → `develop` merge — the merged tip's first parent is then the named sha.
- Nothing else lands on `develop` between that staged verdict commit and the merge.
- The ship PR's verdict is consumed and deleted after the `main` merge, like any other.
