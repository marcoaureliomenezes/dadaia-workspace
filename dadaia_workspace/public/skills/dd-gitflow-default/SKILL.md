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
- Any bug fix (`dd-bug-resolution`).

## 2. Steps

1. `git fetch --all --prune`.
2. Diff `main` against `develop` — a nonzero diff means `develop` carries undeployed work.
3. Identify the one live `feature/{M.m.p}` branch.
4. Surface a `feature/{v}` predating `develop`'s last move to the operator first — it is stale.
5. Branch count, cut point and name follow `DADAIA.md` §4.2 — never restated here.
6. Definition stage: author the candidate's SPEC/PLAN/TASKS at the release root on `feature/{M.m.p}`.
7. Implementation stage: one commit per completed task group, shaped per §3a.
8. Candidate closure: open one `feature/{M.m.p}` → `develop` PR and merge it green.
9. After the merge, ask the operator: **promote or continue?** Continue = `dadaia release rc-archive`; promote = step 10.
10. Promote: open the PR `develop` → `main` (ship verdict pre-staged naming develop's tip, §3b).
11. The moment it merges, run `dadaia release archive <v> --shipped <sha> --pr <n> --next <M.m.p>` — it ships, archives, appends the histo record and births the next release, then PRINTS the git `next:` lines: delete `feature/{M.m.p}`, cut `feature/{next}` from `main`, then `git merge -s ours origin/develop` — run them in that order.
12. Tag `archive/<name>` then delete a branch the moment its work lands elsewhere.

## 3a. Commit shapes — each write alone, in its own shape

| # | Write | Staged set | Message |
|---|---|---|---|
| 1 | Bug registration | `specs/bugs/BUGS.jsonl` alone | `chore(bugs): report <id>` |
| 2 | Backlog / ADR | `BACKLOG.json` alone, or `ADRs/decisions.jsonl` alone | `chore(backlog): …` / `chore(adrs): …` |
| 3 | Bug fix | code + regression test + the `BUGS.jsonl` line, together | `fix(bugs): <id> — <cause>` |
| 4 | Resolve record | commits only; a push happens when asked, `dadaia ci preflight` first | — |
| 5 | Release definition | SPEC + PLAN + TASKS + the picked entries flipped to `status: picked` + picked bugs, one commit | `feat(specs): define candidate …` |
| 6 | Task implementation | the task's declared write set | `conventional-commit(task-id): description` — the auditable trace |

## 3b. The ship-PR verdict

- Stage the verdict naming develop's CURRENT tip as the last commit on
  `feature/{M.m.p}`, before the final `feature` → `develop` merge — the merged tip's
  first parent is then the named sha.
- Nothing else lands on `develop` between that staged verdict commit and the merge.
- The verdict store is two-hop: PR head, or the head's first parent
  (`features/chokepoints/verdict.py::covering_verdict`).
- On disk a verdict is live while it names the head, the head's first parent, or
  `origin/develop`'s tip — one file per sha; anything else is stale, refused by the
  pre-push gate and deleted by `dadaia doctor --fix` (SPEC-DOC-044, one rule:
  `features/chokepoints/verdict.py::live_verdict_shas`).
- The ship PR's verdict is consumed and deleted after the `main` merge, like any
  other.

## 4. Done when

- Every commit for a release traces to a candidate's definition, implementation,
  closure merge, or a bug fix — each write alone in its §3a shape, verifiable by
  `git log`.
- Every staged verdict names a sha the merge will consume; no survivor on disk.

## 5. References

- `DADAIA.md` §4 — the branch-contract law this skill operates.
- [`CICD-AUTOMATION.md`](CICD-AUTOMATION.md) — CI/CD checks to suggest a consumer operator.
- Mechanical enforcement (pre-push hook / CI): branch-name pattern, push refusal,
  denylist scan, `pr-source-guard`, verdict-gate job requiring an APPROVED security
  handoff. Everything else in this skill is discipline, upheld by agents and
  reviewers, unenforced by any hook.
