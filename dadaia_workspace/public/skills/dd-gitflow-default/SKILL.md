---
name: dd-gitflow-default
description: >
  The branch and commit contract (§2a, §3a): which branch to cut and push, the commit shape of each write, and the PR gate. Use when branching, writing a commit message, opening or merging a PR, or promoting; task and job order is dd-release-implementation's.
---

# dd-gitflow-default — The Branch Contract

The branch contract by role; the names are `specs/constitution.md`'s `gitflow:` block (`<work>M.m.p` = work prefix + version).

## 1. When

- Start of any session touching git.
- Branching, committing, opening a PR.
- Any bug fix (`dd-bug-resolution`).

## 2. Steps

1. `git fetch --all --prune`.
2. Read the gitflow block; diff the principal against the integration branch — a nonzero diff (`git diff --quiet origin/<principal> origin/<integration>` exits 1) means the integration branch carries undeployed work.
3. Identify the one live work branch `<work>M.m.p`.
4. Surface a work branch predating the integration branch's last move (`git merge-base --is-ancestor origin/<integration> origin/<work>` exits 1) to the operator first — it is stale.
5. Branch count, cut point and name follow §2a.
6. Definition stage: where a candidate is defined is `specs/releases/AGENTS.md`'s.
7. Implementation stage: one commit per task, shaped per §3a.
8. Candidate closure: open one work → integration PR and merge it green.
9. After the merge, the main thread asks the operator: **promote or continue?** Continue = the next candidate's `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id>`; promote = step 10.
10. Promote: open the PR integration → principal (the reviewer's `APPROVED` on the integration tip, §3b); its merge is the deploy.
11. The moment the promote PR merges, record it — `python3 .agents/skills/dd-release-implementation/scripts/release.py ship --sha <sha>` — then delete the work branch and cut the next one per §2a.
12. `git tag archive/<name> <name>` then `git branch -d <name>` the moment its work lands elsewhere.

## 2a. The branch contract

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| work `<work>M.m.p` | Yes — valid name (run `verify:` first) | integration | its jobs' worktree merges |
| integration | No — advances only by PR | principal (bootstrap only) | PR from the row above, one per candidate |
| principal | No — advances only by PR | — | PR from the integration branch, at the final `rc` |
| job `wt/<M.m.p>-rc<N>/<job>` | Yes — valid name (not `define`) | work | its worktree merge (`worktrees/AGENTS.md` §2) |
| backlog `wt/backlog/<slug>` | Yes | work | its worktree merge (`worktrees/AGENTS.md` §2) |
| task `wt/<M.m.p>-rc<N>/<job>--<task-id>` | No | its job branch | its worktree merge (`worktrees/AGENTS.md` §2) (its task gate) |
| plain `wt/<name>` | No — local only | the live work branch, else the checked-out branch, recorded | its reviewed worktree merge, with optional `verify:` |

- No `v` prefix or suffix; a hotfix job is `wt/hotfix/<bug-id>`, local only, landing by its worktree merge (`worktrees/AGENTS.md` §2).
- Exactly one live work branch, named for the live release; a job — a bug fix included — reaches it through its own worktree (`worktrees/AGENTS.md` §1).

## 3a. Commit shapes — each write in its own shape

`<code>` is any path outside `specs/`; `<id>` is the current task id `J<n>.T<k>`.

| # | Tree | Write | Message |
|---|---|---|---|
| 1 | a job, `backlog/<slug>` | Bug registration: `specs/bugs/BUGS.jsonl` | `chore(bugs): report <id>` |
| 2 | `backlog/<slug>` | Backlog entry or exit: `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl` | `chore(backlog): …` |
| 2 | `backlog/<slug>`, `define` | ADR proposal or in-place `measured_by` repair: `specs/ADRs/decisions.jsonl` | `docs(adr): propose <slug>` / `chore(adrs): repair …` |
| 2 | `define`, `reconcile` | ADR acceptance with its canonical-memory hunk: `specs/ADRs/decisions.jsonl`, `specs/memory/*` | `docs(adr): accept <slug>` |
| 3 | a job | Bug fix or REBUILD: `<code>`, red loop in the body, a hotfix's naming `block: <item>`; the regression test lands first as a `test(` commit (a task's shape 6, or the hotfix tree's) | `fix(bugs): <id> — <cause>`; a REBUILD `refactor(bugs): <id> — REBUILD <unit>: …`; a group names its N ids |
| 4 | a job | Terminal transition without code (`resolve` after its named shape-3 fix commit, `supersede`, `reject`): `specs/bugs/BUGS.jsonl` | `chore(bugs): <verb> <id> — <reason, by task-id, or fix sha>`; per class `chore(bugs): <verb> class <class> — <reason>`, one id per body line |
| 4 | a job | Archive terminal bugs: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl` | `chore(bugs): archive <ids>` |
| 5 | `define` | Release definition: `specs/releases/<v>/rc-<N>/*` | `feat(specs): define candidate …` |
| 6 | a task tree | Task: its `W:` | `conventional-commit(<id>): description`, a REBUILD `refactor(<id>): REBUILD <unit> — …` |
| 8 | `define` | SPEC and PLAN approval: `specs/releases/<v>/rc-<N>/{SPEC,PLAN}.md` | `docs(specs): …` |
| 9 | `reconcile` | Memory pass and derived docs: `specs/memory/*`, `README.md`, `llms.txt`, `docs/*.md` | `docs(memory): …` |
| 10 | `define`, `reconcile` | Release state: `specs/releases/<v>/_RELEASE.json`, only when [`RELEASE-EVENTS.md`](../dd-release-implementation/RELEASE-EVENTS.md) requires a current entry | `chore(release): …` |

## 3b. The PR gate

- Both PR edges require the repo's `verify:` line green and a `dd-code-reviewer` APPROVED verdict, security lens included, on the PR head.
- The reviewer's verdict is pasted verbatim into the PR as a quote by the main thread; that quote is the verdict's only record, since no script checks a PR.

## 4. Done when

- `git branch -a` lists only §2a branches, and every commit since the work branch's cut matches one §3a row.

## 5. References

- Run `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py --help` (verbs `new`, `merge`, `clean`, `hash`, `list`); run it, never read its source; the rules: `worktrees/AGENTS.md`.
- [`CICD-AUTOMATION.md`](CICD-AUTOMATION.md) — optional: plug your own pipeline into the repo's `verify:` lines.
- Push chokepoints: `.dadaia/AGENTS.md` §3; every other rule here is discipline upheld by agents and reviewers.
