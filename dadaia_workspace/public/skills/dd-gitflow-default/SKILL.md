---
name: dd-gitflow-default
description: >
  The branch and commit contract (§2a, §3a): which branch to cut and push, the commit shape of each write, and the merge gate. Use when branching, writing a commit message, merging, or promoting; task and job order is dd-release-implementation's.
---

# dd-gitflow-default — The Branch Contract

The branch contract by role; the names are `specs/constitution.md`'s `gitflow:` block (`<work>M.m.p` = work prefix + version).

## 1. When

- Start of any session touching git.
- Branching, committing, merging.
- Any bug fix (`dd-bug-resolution`).

## 2. Steps

1. `git fetch --all --prune`.
2. Ref R is `origin/R` when the repo has a remote, else the local `R`. Read the gitflow block; branch B lacks a change branch A holds when `git merge-tree --write-tree B A` prints a tree other than `git rev-parse B^{tree}` (git ≥ 2.38); the integration branch carries undeployed changes when the principal lacks a change it holds.
3. Identify the one live work branch `<work>M.m.p`.
4. Report a work branch that lacks a change the integration branch holds (step 2's test, B the work branch, A the integration branch) first — it is stale.
5. Branch count, cut point and name follow §2a.
6. Definition stage: where a candidate is defined is `specs/releases/AGENTS.md`'s.
7. Implementation stage: one commit per task, shaped per §3a.
8. Candidate closure, on the operator's explicit order (publication): merge the work → integration branch, green (§3b); before that order, "finish" means merged into the work branch.
9. When a candidate closes — its work → integration merge, or, before the operator's order, its `wt-rc` merged into the work branch — the main thread asks the operator one question: **promote or continue?** — and, for promote, the next release `<id>` or none. Continue = the next candidate's `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id> --specs <specs-dir>`; promote = step 10.
10. Promote: merge integration → principal (the reviewer's `APPROVED` on its head, §3b); the pipeline PR the project's own release pipeline then opens into the principal, if any, is the promote PR whose merge deploys, else the integration → principal merge is.
11. After the promote merges, tag the work tip as `archive/<work-name>`; once the next release `<id>` is named (step 9), rename the work branch, never cut a new one: `git -C <repo> branch -m <work><old> <work><id>` (and its remote ref `origin/<work><old>`, when one exists: `git -C <repo> push -u origin <work><id> :<work><old>`). On it a `wt-backlog-<slug>` lane ships the release, its carry owned by `dd-release-implementation/RELEASE-EVENTS.md`, then the new candidate starts in its `wt-rc` (step 9). Until then work continues on the old-named branch; the rename carries every commit, the ship included, to the next work → integration merge.
12. A `.dadaia/.venv/bin/dadaia worktree` tree and its branch complete under `worktrees/AGENTS.md` §2, which owns their merge and cleanup lifecycle.

- Rewriting the pushed history of, or force-pushing, a branch the gitflow block names is refused unless the operator authorizes that act in its own turn.

## 2a. The branch contract

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| work `<work>M.m.p` | Yes — valid name (each `wt-rc` and hotfix merge into it ran `verify:`; no rerun before a push) | integration | its `wt-rc` and lane merges, and direct `specs/audits/**` commits |
| integration | Yes | — | the work → integration merge (step 8) |
| principal | Yes | — | the integration → principal merge (step 10), or the pipeline PR the project's own release pipeline opens |
| rc `wt/<M.m.p>/rc-<N>/wt-rc` | Yes | work | its merge into the work branch (`worktrees/AGENTS.md` §2) |
| job `wt/<M.m.p>/rc-<N>/job-<n>/wt-main` | Yes | its `wt-rc` | its merge into `wt-rc` (`worktrees/AGENTS.md` §2) |
| task `wt/<M.m.p>/rc-<N>/job-<n>/wt-task-<kkk>` | No | its `wt-main` | its merge into `wt-main` (its task gate) |
| lane `wt/<M.m.p>/wt-backlog-<slug>` (Yes), `wt/<M.m.p>/wt-hotfix-<bug-id>` (No, local only) | as named | work | its merge into the work branch (`worktrees/AGENTS.md` §2) |

- No `v` prefix or suffix; leaf names: `worktrees/AGENTS.md` §1.
- Exactly one live work branch, cut from the integration branch once and renamed at each promote (§2 step 11): named for the live release, or for the next release's `<id>` once a promote named it; every change but an audit reaches it through an rc's `wt-rc` or a lane (`worktrees/AGENTS.md` §1).

## 3a. Commit shapes — each write in its own shape

`<code>` is any path outside `specs/`; `<id>` is the bug id in shapes 1, 3 and 4, and in shape 6 the current task id `J<n>.T<k>` (in a lane, its `<slug>`).

| # | Tree | Write | Message |
|---|---|---|---|
| 1 | `wt-main`, `wt-backlog-<slug>`, `wt-rc (closure)` | Bug registration: `specs/bugs/BUGS.jsonl` | `chore(bugs): report <id>` |
| 2 | `wt-backlog-<slug>`, `wt-rc` (reconcile) | Backlog entry or exit: `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl` | `chore(backlog): …` |
| 2 | `wt-backlog-<slug>`, `wt-rc` (define) | ADR proposal: `specs/ADRs/decisions.jsonl` | `docs(adr): propose <slug>` |
| 2 | `wt-backlog-<slug>`, `wt-rc` (define, reconcile) | In-place `measured_by` repair: `specs/ADRs/decisions.jsonl` | `chore(adrs): repair …` |
| 2 | `wt-rc` (define, reconcile) | ADR acceptance or rejection: `specs/ADRs/decisions.jsonl`, `specs/memory/*` | `docs(adr): accept <slug>` or `docs(adr): reject <slug>` |
| 3 | a `wt-task-<kkk>` or `wt-hotfix` tree, `wt-rc (closure)` | Bug fix or REBUILD: `<code>` and the tracked `specs/**/AGENTS.md` mirrors its own scaffold or template change re-renders, by the doctor's render; red loop in the body, `block: <item>` where `specs/bugs/AGENTS.md` §2 requires it; the regression test lands first as a `test(` commit (a task's shape 6, or the lane's) | `fix(bugs): <id> — <cause>`; a REBUILD `refactor(bugs): <id> — REBUILD <unit>: …`; a group names its N ids |
| 3 | a `wt-task-<kkk>` or `wt-hotfix` tree, `wt-rc (closure)` | A fix that is itself a test change: the test files | `test(<id>): …`; the body carries the `fix(bugs): <id> — <cause>` line, the record's cited fix |
| 4 | a `wt-main`, `wt-hotfix`, `wt-backlog-<slug>` tree or `wt-rc (closure)` | Terminal transition without code (`resolve` after its named shape-3 fix commit, `supersede`, `reject`): `specs/bugs/BUGS.jsonl` | `chore(bugs): <verb> <id> — <reason, by task-id, or fix sha>`; per class `chore(bugs): <verb> class <class> — <reason>`, one id per body line |
| 4 | a `wt-main`, `wt-hotfix`, `wt-backlog-<slug>` tree or `wt-rc (closure)` | Governance update without a status change (`bugs.py update`): `specs/bugs/BUGS.jsonl` | `chore(bugs): update <id> — <field>: <reason>` |
| 4 | any lane, a `wt-main` job tree or `wt-rc` (reconcile) | Archive terminal bugs: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl` | `chore(bugs): archive <ids>` |
| 5 | `wt-rc` (define) | Release definition, and a candidate's birth (`release.py new` writes `_RELEASE.json` and the SPEC stub in one transaction): `specs/releases/<v>/rc-<N>/*`, `specs/releases/<v>/_RELEASE.json` | `feat(specs): define candidate …` |
| 6 | a task tree, or a `wt-backlog-<slug>` lane (the repo's `AGENTS.md` alone) | Task: its `W:` | `conventional-commit(<id>): description`, a REBUILD `refactor(<id>): REBUILD <unit> — …` |
| 7 | `wt-hotfix-<bug-id>` | Specs revert, no code: the `specs/` paths of the culprit commit, put back | `Revert "<subject>"`; body `This reverts commit <sha>.` |
| 8 | `wt-rc` (define), a `wt-backlog-<slug>` lane on the operator's order | SPEC and PLAN approval: `specs/releases/<v>/rc-<N>/{SPEC,PLAN}.md`; the lane: `specs/constitution.md`, a `specs/AGENTS.md` re-render | `docs(specs): …` |
| 9 | `wt-rc` (reconcile) | Memory pass and derived docs: `specs/memory/*`, `README.md`, `docs/*.md` | `docs(memory): …` |
| 9 | the `wt-backlog-first-pass` lane | Memory pass: `specs/memory/*` | `docs(memory): …` |
| 9 | a `wt-backlog-<slug>` lane on the operator's order | Canonical-memory rewrite: `specs/memory/ARCHITECTURE.md`, `specs/memory/QUALITY.md` | `docs(memory): …` |
| 10 | `wt-rc` (define, reconcile), a `wt-backlog-<slug>` lane on the next work branch (§2 step 11, `ship`) | Release state: `specs/releases/<v>/_RELEASE.json` and `specs/releases/_archive/**`, only when [`RELEASE-EVENTS.md`](../dd-release-implementation/RELEASE-EVENTS.md) requires a current entry | `chore(release): …` |
| 11 | the job tree that found the defect (`wt-main`) | Pure law or doc text that no program prints (a fix line, `--help` or a schema stays Arm B, shape 3): the file it corrects; no `BUGS.jsonl` record | `docs(law): <what>`; the body cites the finding; one review |
| 12 | a `wt-task-<kkk>` or `wt-hotfix` tree | Code revert: the culprit commit's paths, put back | `Revert "<subject>"`; body `This reverts commit <sha>.` |
| 13 | a `wt-task-<kkk>` or `wt-hotfix` tree | Format-only commit: shape 6's `style(<id>): …`, never a `fix(bugs)` or `refactor(bugs)` line, since a record's fix is the newest id-line commit (`dd-bug-resolution/LINEAGE.md` §The filter) | `style(<id>): …` |

## 3b. The merge gate

- The merges of steps 8 and 10 require the repo's `verify:` line green and a `dd-code-reviewer` APPROVED verdict, security lens included, on the merged head; through a PR when the host has one. The project's own pipeline PR into the principal stays outside this gate.
- A PR merge: the main thread quotes the verdict in it verbatim, its only record; no script checks it.

## 4. Done when

- Current branches match §2a, and every commit since the work branch's cut, `specs/audits/**` commits aside, matches one §3a row.
- After a work → integration merge: the merge gate (§3b) holds.
- After promotion: the `archive/<work-name>` tag resolves to the former work tip, once the next release is named the work branch carries its name and its first merge records the principal merge as `shipped` in the archived state.

## 5. References

- `.dadaia/.venv/bin/dadaia worktree --help` lists the verbs; run it, never read its source; the rules: `worktrees/AGENTS.md`.
- [`CICD-AUTOMATION.md`](CICD-AUTOMATION.md) — optional: plug your own pipeline into the repo's `verify:` lines.
- Chokepoints: `.dadaia/AGENTS.md` §3 and `worktrees/AGENTS.md`; every other rule here is discipline upheld by agents and reviewers.
