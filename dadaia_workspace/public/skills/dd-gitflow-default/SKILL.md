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
8. Candidate closure, on the operator's explicit order (publication): open one work → integration PR and merge it green; before that order, "finish" means merged into the work branch.
9. After the merge, the main thread asks the operator one question: **promote or continue?** — and, for promote, the next release `<id>` or none. Continue = the next candidate's `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id>`; promote = step 10.
10. Promote: open the PR integration → principal (the reviewer's `APPROVED` on the integration tip, §3b); its merge is the deploy.
11. After the promote PR merges, tag the work tip as `archive/<work-name>`; once the next release `<id>` is named (step 9), rename the work branch, never cut a new one: `git -C <repo> branch -m <work><old> <work><id>` (and its remote ref, when one exists: `git -C <repo> push -u origin <work><id> :<work><old>`). On it a `wt-backlog-<slug>` lane runs `python3 .agents/skills/dd-release-implementation/scripts/release.py ship --sha <sha>`, then `release.py new <id>` in the new candidate's `wt-rc`. Until then work continues on the old-named branch; the rename carries every commit, the ship included, to the next work → integration PR.
12. A `.dadaia/.venv/bin/dadaia worktree` tree and its branch complete under `worktrees/AGENTS.md` §2, which owns their merge and cleanup lifecycle.

- Rewriting the pushed history of, or force-pushing, the work branch or a branch that advances only by PR is refused unless the operator authorizes that act in its own turn.

## 2a. The branch contract

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| work `<work>M.m.p` | Yes — valid name (each `wt-rc` and hotfix merge into it ran `verify:`; no rerun before a push) | integration | its `wt-rc` and lane merges, and direct `specs/audits/**` commits |
| integration | No — advances only by PR | principal (bootstrap only) | PR from the row above, one per candidate |
| principal | No — advances only by PR | — | PR from the integration branch, at the final `rc` |
| rc `wt/<M.m.p>/rc-<N>/wt-rc` | Yes | work | its merge into the work branch (`worktrees/AGENTS.md` §2) |
| job `wt/<M.m.p>/rc-<N>/job-<n>/wt-main` | Yes | its `wt-rc` | its merge into `wt-rc` (`worktrees/AGENTS.md` §2) |
| task `wt/<M.m.p>/rc-<N>/job-<n>/wt-task-<kkk>` | No | its `wt-main` | its merge into `wt-main` (its task gate) |
| lane `wt/<M.m.p>/wt-backlog-<slug>` (Yes), `wt/<M.m.p>/wt-hotfix-<bug-id>` (No, local only) | as named | work | its merge into the work branch (`worktrees/AGENTS.md` §2) |

- No `v` prefix or suffix; leaf names: `worktrees/AGENTS.md` §1.
- Exactly one live work branch, cut from the integration branch once and renamed at each promote (§2 step 11): named for the live release, or for the next release's `<id>` once a promote named it; every change but an audit reaches it through an rc's `wt-rc` or a lane (`worktrees/AGENTS.md` §1).

## 3a. Commit shapes — each write in its own shape

`<code>` is any path outside `specs/`; `<id>` is the current task id `J<n>.T<k>`, in a lane its `<slug>`.

| # | Tree | Write | Message |
|---|---|---|---|
| 1 | `wt-main`, `wt-backlog-<slug>` | Bug registration: `specs/bugs/BUGS.jsonl` | `chore(bugs): report <id>` |
| 2 | `wt-backlog-<slug>`, `wt-rc` (reconcile) | Backlog entry or exit: `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl` | `chore(backlog): …` |
| 2 | `wt-backlog-<slug>`, `wt-rc` (define) | ADR proposal: `specs/ADRs/decisions.jsonl` | `docs(adr): propose <slug>` |
| 2 | `wt-backlog-<slug>`, `wt-rc` (define, reconcile) | In-place `measured_by` repair: `specs/ADRs/decisions.jsonl` | `chore(adrs): repair …` |
| 2 | `wt-rc` (define, reconcile) | ADR acceptance or rejection: `specs/ADRs/decisions.jsonl`, `specs/memory/*` | `docs(adr): accept <slug>` or `docs(adr): reject <slug>` |
| 3 | a `wt-task-<kkk>` or `wt-hotfix` tree | Bug fix or REBUILD: `<code>`, red loop in the body, a hotfix's naming `block: <item>`; the regression test lands first as a `test(` commit (a task's shape 6, or the hotfix lane's) | `fix(bugs): <id> — <cause>`; a REBUILD `refactor(bugs): <id> — REBUILD <unit>: …`; a group names its N ids |
| 4 | a `wt-main` or `wt-hotfix` tree | Terminal transition without code (`resolve` after its named shape-3 fix commit, `supersede`, `reject`): `specs/bugs/BUGS.jsonl` | `chore(bugs): <verb> <id> — <reason, by task-id, or fix sha>`; per class `chore(bugs): <verb> class <class> — <reason>`, one id per body line |
| 4 | `wt-rc` (reconcile) | Archive terminal bugs: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl` | `chore(bugs): archive <ids>` |
| 5 | `wt-rc` (define) | Release definition, and a candidate's birth (`release.py new` writes `_RELEASE.json` and the SPEC stub in one transaction): `specs/releases/<v>/rc-<N>/*`, `specs/releases/<v>/_RELEASE.json` | `feat(specs): define candidate …` |
| 6 | a task tree, or a `wt-backlog-<slug>` lane (the repo's `AGENTS.md` alone) | Task: its `W:` | `conventional-commit(<id>): description`, a REBUILD `refactor(<id>): REBUILD <unit> — …` |
| 7 | `wt-hotfix-<bug-id>` | Specs revert, no code: the `specs/` paths of the culprit commit, put back | `Revert "<subject>"`; body `This reverts commit <sha>.` and `block: <item>` |
| 8 | `wt-rc` (define) | SPEC and PLAN approval: `specs/releases/<v>/rc-<N>/{SPEC,PLAN}.md` | `docs(specs): …` |
| 9 | `wt-rc` (reconcile) | Memory pass and derived docs: `specs/memory/*`, `README.md`, `docs/*.md` | `docs(memory): …` |
| 9 | the `wt-backlog-first-pass` lane | Memory pass: `specs/memory/*` | `docs(memory): …` |
| 10 | `wt-rc` (define, reconcile), a `wt-backlog-<slug>` lane on the next work branch (§2 step 11, `ship`) | Release state: `specs/releases/<v>/_RELEASE.json` and `specs/releases/_archive/**`, only when [`RELEASE-EVENTS.md`](../dd-release-implementation/RELEASE-EVENTS.md) requires a current entry | `chore(release): …` |

## 3b. The PR gate

- Both PR edges require the repo's `verify:` line green and a `dd-code-reviewer` APPROVED verdict, security lens included, on the PR head.
- The reviewer's verdict is pasted verbatim into the PR as a quote by the main thread; that quote is the verdict's only record, since no script checks a PR.

## 4. Done when

- Current branches match §2a, and every commit since the work branch's cut, `specs/audits/**` commits aside, matches one §3a row.
- After a work → integration PR: the repo's `verify:` line passed, the reviewer's `APPROVED` verdict names the PR head, and the PR merged.
- After promotion: the `archive/<work-name>` tag resolves to the former work tip, once the next release is named the work branch carries its name and its first merge records the principal merge as `shipped` in the archived state.

## 5. References

- Run `.dadaia/.venv/bin/dadaia worktree --help` (verbs `new`, `merge`, `sync`, `clean`, `hash`, `list`); run it, never read its source; the rules: `worktrees/AGENTS.md`.
- [`CICD-AUTOMATION.md`](CICD-AUTOMATION.md) — optional: plug your own pipeline into the repo's `verify:` lines.
- Chokepoints: `.dadaia/AGENTS.md` §3 and `worktrees/AGENTS.md`; every other rule here is discipline upheld by agents and reviewers.
