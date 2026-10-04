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
6. Definition stage: author the candidate's SPEC/PLAN/TASKS in its `rc-<N>/` on the work branch.
7. Implementation stage: one commit per completed task group, shaped per §3a.
8. Candidate closure: open one work → integration PR and merge it green.
9. After the merge, ask the operator: **promote or continue?** Continue = the next candidate's `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id>`; promote = step 10.
10. Promote: open the PR integration → principal (ship verdict pre-staged naming the integration tip, §3b); its merge is the deploy.
11. The moment the promote PR merges, record it — `python3 .agents/skills/dd-release-implementation/scripts/release.py ship --sha <sha> --pr <n>` — then delete the work branch and cut the next one per §2a.
12. Tag `archive/<name>` then delete a branch the moment its work lands elsewhere.

## 2a. The branch contract

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| work `<work>M.m.p` | Yes — the repo's own CI checks green + valid name | integration | the PR below |
| integration | No — never a direct push | principal (bootstrap only) | PR from the row above, at definition `Approved` and at each `rc` merge |
| principal | No — never a direct push | — | PR from the integration branch, at the final `rc` |

- No `v` prefix, no suffix, no other branch we cut; `hotfix/*` is retired (operator request only, no cadence).
- Exactly one live work branch, named for the live release; a bug fix reaches it in any phase through a `bug` worktree (`worktrees/AGENTS.md` §2).
- Each candidate closure burns one work -> integration merge; after it, ask the operator: promote or continue.
- Every flow stage runs on the work branch; the other two are PR targets only, never a working branch.

## 3a. Commit shapes — each write in its own shape

A commit stages only paths its worktree kind's allowed set holds (`_worktree_kinds.KINDS`, `worktrees/AGENTS.md`); `<code>` is any path outside `specs/`.

| # | Kind | Write | Message |
|---|---|---|---|
| 1 | `bug`, `backlog` | Bug registration: `specs/bugs/BUGS.jsonl` | `chore(bugs): report <id>` |
| 2 | `backlog` | Backlog entry or exit: `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl` | `chore(backlog): …` |
| 2 | `backlog`, `release` | ADR proposal or in-place `measured_by` repair (ADR 0138): `specs/ADRs/decisions.jsonl` | `docs(adr): propose <slug>` / `chore(adrs): repair …` |
| 2 | `release` | ADR acceptance with its canonical-memory hunk: `specs/ADRs/decisions.jsonl`, `specs/memory/*` | `docs(adr): accept <slug>` |
| 3 | `bug` | Bug fix: `<code>` + regression test + its `specs/bugs/BUGS.jsonl` line, red loop quoted in the body | `fix(bugs): <id> — <cause>` |
| 4 | `bug` | Terminal transition without code (`resolve` by a task, `supersede`, `defer`, `reject`): `specs/bugs/BUGS.jsonl` | `chore(bugs): <verb> <id> — <reason, or by <task-id> (<sha>)>` |
| 5 | `release` | Release definition: the trio, one commit, `specs/releases/<v>/rc-<N>/*` | `feat(specs): define candidate …` |
| 6 | `impl` | Task implementation: its `W:` (`<code>`) | `conventional-commit(task-id): description` — the auditable trace |
| 7 | `impl` | Task marker (the releases law §3): `specs/releases/<v>/rc-<N>/TASKS.md` | `chore(tasks): <verb> <id>` |
| 8 | `release` | Trio amendment or approval: `specs/releases/<v>/rc-<N>/SPEC.md` | `docs(specs): …` |
| 9 | `release` | Closure memory pass: `specs/memory/*` | `docs(memory): …` |
| 10 | `release` | Release state: `specs/releases/<v>/_RELEASE.json` | `chore(release): …` |

## 3b. The PR gate

- Both PR edges require CI green (lint, typecheck, tests, doctor, gitleaks) and a
  `dd-code-reviewer` APPROVED verdict, security lens included, on the PR head. The ruleset
  is the operator's.
- No CI job of a context's main repo or associated repos calls a model API, except an
  evals repo's, under every clause below:
  - a model-calling job runs only on `workflow_dispatch` or `schedule`, never `push`,
    `pull_request` or `pull_request_target`;
  - no workflow of an evals repo runs on a self-hosted runner;
  - the model secret is read only by those jobs, at job level;
  - artifacts and transcripts come only from synthetic projects built in the run;
  - every artifact and the job summary pass a secret scan, the model secret's value
    included, before any upload and before the summary is written; a hit fails the job
    and uploads nothing.

## 4. Done when

- Every commit for a release traces to a candidate's definition, implementation,
  closure merge, or a bug fix — each write in its §3a shape, verifiable by
  `git log`.

## 5. References

- `scripts/worktree.py` — opens, lists, merges and cleans worktrees; the rules: `worktrees/AGENTS.md`.
- [`CICD-AUTOMATION.md`](CICD-AUTOMATION.md) — CI/CD checks to suggest a consumer operator.
- Mechanical enforcement (pre-push hook / CI): branch-name pattern, push refusal,
  denylist scan, `pr-source-guard`. Everything else in this skill is discipline, upheld by agents and
  reviewers, unenforced by any hook.
