---
name: dd-gitflow-default
description: >
  The three-branch contract whenever git is touched: when to start work, which
  branch to cut, how a release rides it, the isolated commit shapes, and what gates
  a push. Use when branching, committing, opening a PR, or starting a task.
---

# dd-gitflow-default — The Branch Contract

The branch contract by role; the names are `specs/constitution.md`'s `gitflow:` block (`<work>M.m.p` = work prefix + version).

## 1. When

- Start of any session touching git.
- Branching, committing, opening a PR, or starting a task.
- Any bug fix (`dd-bug-resolution`).

## 2. Steps

1. `git fetch --all --prune`.
2. Read the gitflow block; diff the principal against the integration branch — a nonzero diff means the integration branch carries undeployed work.
3. Identify the one live work branch `<work>M.m.p`.
4. Surface a work branch predating the integration branch's last move to the operator first — it is stale.
5. Branch count, cut point and name follow §2a.
6. Definition stage: where a candidate is defined is `specs/releases/AGENTS.md`'s.
7. Implementation stage: one commit per task, shaped per §3a.
8. Candidate closure: open one work → integration PR and merge it green.
9. After the merge, ask the operator: **promote or continue?** Continue = the next candidate's `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id>`; promote = step 10.
10. Promote: open the PR integration → principal (ship verdict pre-staged naming the integration tip, §3b); its merge is the deploy.
11. The moment the promote PR merges, record it — `python3 .agents/skills/dd-release-implementation/scripts/release.py ship --sha <sha>` — then delete the work branch and cut the next one per §2a.
12. Tag `archive/<name>` then delete a branch the moment its work lands elsewhere.

## 2a. The branch contract

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| work `<work>M.m.p` | Yes — its `verify:` line green + valid name | integration | the PR below |
| job `wt/<M.m.p>-rc<N>/<job>` | Yes — valid name | work | its worktree merge (`worktrees/AGENTS.md` §2) |
| backlog `wt/backlog/<slug>` | Yes | work | its worktree merge (`worktrees/AGENTS.md` §2) |
| task `wt/<M.m.p>-rc<N>/<job>--<task-id>` | No | its job branch | its worktree merge (`worktrees/AGENTS.md` §2) (its task gate) |
| plain `wt/<name>` | No — local only | current branch, recorded as its base | its reviewed worktree merge, with optional `verify:` |
| integration | No — never a direct push | principal (bootstrap only) | PR from the row above, one per candidate |
| principal | No — never a direct push | — | PR from the integration branch, at the final `rc` |

- No `v` prefix or suffix; aside from the local-only plain row, no other branch is cut; no
  `hotfix/*` branch (a hotfix is a job, bugs law §2).
- Exactly one live work branch, named for the live release; a job — a bug fix included — reaches it through its own worktree (`worktrees/AGENTS.md` §1).
- Every flow stage runs on the work branch; the other two are PR targets only, never a working branch.

## 3a. Commit shapes — each write in its own shape

A job and its task trees hold code, tests, specs, memory and derived docs alike (`worktrees/AGENTS.md` §1); the shape names the write, never a tree. `<code>` is any path outside `specs/`; `<id>` is the current task id `J<n>.T<k>`.

| # | Tree | Write | Message |
|---|---|---|---|
| 1 | a job, `backlog/<slug>` | Bug registration: `specs/bugs/BUGS.jsonl` | `chore(bugs): report <id>` |
| 2 | `backlog/<slug>` | Backlog entry or exit: `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl` | `chore(backlog): …` |
| 2 | `backlog/<slug>`, `define` | ADR proposal or in-place `measured_by` repair (ADR 0138): `specs/ADRs/decisions.jsonl` | `docs(adr): propose <slug>` / `chore(adrs): repair …` |
| 2 | `define`, `reconcile` | ADR acceptance with its canonical-memory hunk: `specs/ADRs/decisions.jsonl`, `specs/memory/*` | `docs(adr): accept <slug>` |
| 3 | a job | Bug fix: `<code>` + its `specs/bugs/BUGS.jsonl` line, red loop in the body, a hotfix's naming `block: <item>`; the regression test lands first in its RED-test task (shape 6) | `fix(bugs): <id> — <cause>`; a REBUILD `refactor(bugs): <id> — REBUILD <unit>: …`; a group names its N ids |
| 4 | a job | Terminal transition without code (`resolve` by a task, `supersede`, `reject`): `specs/bugs/BUGS.jsonl` | `chore(bugs): <verb> <id> — <reason, or by <task-id> (<sha>)>`; per class `chore(bugs): <verb> class <class> — <reason>`, one id per body line |
| 4 | a job | Archive terminal bugs: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl` | `chore(bugs): archive <ids>` |
| 5 | `define` | Release definition: `specs/releases/<v>/rc-<N>/*` | `feat(specs): define candidate …` |
| 6 | a task tree | Task: its `W:` | `conventional-commit(<id>): description`, a REBUILD `refactor(<id>): REBUILD <unit> — …` |
| 8 | `define` | Trio approval: `specs/releases/<v>/rc-<N>/SPEC.md` | `docs(specs): …` |
| 9 | `reconcile` | Memory pass and derived docs: `specs/memory/*`, `README.md`, `llms.txt`, `docs/*.md` | `docs(memory): …` |
| 10 | `define`, `reconcile` | Release state: `specs/releases/<v>/_RELEASE.json`, only when [`RELEASE-EVENTS.md`](../dd-release-implementation/RELEASE-EVENTS.md) requires a current entry | `chore(release): …` |

## 3b. The PR gate

- Both PR edges require the repo's `verify:` line green and a `dd-code-reviewer` APPROVED verdict, security lens included, on the PR head.
- The reviewer's verdict is pasted verbatim into the PR as a quote by the main thread; no script gates it and no handoff is written for it.

## 4. Done when

- Every commit for a release traces to a candidate's definition, implementation,
  closure merge, or a bug fix — each write in its §3a shape, verifiable by
  `git log`.

## 5. References

- `scripts/worktree.py` — opens, lists, merges and cleans worktrees; the rules: `worktrees/AGENTS.md`.
- [`CICD-AUTOMATION.md`](CICD-AUTOMATION.md) — optional: plug your own pipeline into the repo's `verify:` lines.
- Mechanical enforcement (pre-push hook / CI): branch-name pattern, push refusal,
  denylist scan, `pr-source-guard`. Everything else in this skill is discipline, upheld by agents and
  reviewers, unenforced by any hook.
