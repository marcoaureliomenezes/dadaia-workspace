---
name: dd-gitflow-default
description: >
  Use whenever git is touched — branching, committing, opening a PR, starting a new task,
  or minting a version. The one operational home of the three-branch model: when to start
  work, which branch to cut, how a release rides it, and what actually gates a push.
  `DADAIA.md` §4 states the law once; this skill is where it operates.
---

# dd-gitflow-default — The Branch Contract, v2

## 1. Start-of-work protocol

Before the first commit of any session:

1. `git fetch --all --prune`.
2. Diff `main` against `develop` — a nonzero diff means `develop` carries undeployed work.
3. Identify the live `feature/{M.m.p}` branch — there is at most one.
4. A `feature/{v}` whose first commit predates `develop`'s last move is **stale** —
   surface it to the operator before touching it.
5. Refuse to create a second `feature/*` branch while one is already live.

*Done when:* you know which branch is live, whether it is stale, and whether `main` and
`develop` are in sync.

## 2. Branch-creation rule

Cut `feature/{next-version}` from `main` only, and only once `{version}` is deployed on
`main`. Name it `M.m.p` — no `v` prefix, no suffix, no fifth pattern.

*Done when:* the new branch exists, is named exactly `M.m.p`, and its parent is `main` at
the just-deployed commit.

## 3. Working the release

| Stage | What happens on `feature/{M.m.p}` |
|---|---|
| Definition | SPEC/PLAN/TASKS authored; PR to `develop` opens the moment the trio is `Aprovado` |
| Implementation | one commit per completed task group |
| `rc` merges | each `rc` burns one `feature/{M.m.p}` → `develop` PR merge; scope is fixes/adjustments to this release only, never new backlog |
| Bugs | fixed on the live feature branch, in any phase — no ceremony, no separate branch (commit shape: §3a) |

*Done when:* every commit for the release traces to one of these four rows.

## 3a. Commit shapes (FR8) — stated once, here

Five isolated write shapes. Each stages nothing else, so the audit can diff it via
`git log` — never a hook (D10).

| # | Shape | What's staged, alone | Commit message |
|---|---|---|---|
| 1 | Bug registration | `specs/bugs/BUGS.jsonl` only (`dadaia bugs append`) | `chore(bugs): report <id>` |
| 2 | Backlog entry / ADR proposal | `specs/backlog/BACKLOG.md` only, or the new `specs/ADRs/NNNN-<slug>.md` only | `chore(backlog): add <slug>` / `docs(adr): propose NNNN-<slug>` |
| 3 | Bug fix — one commit, no second | code + regression test + the `BUGS.jsonl` line, staged together — `dadaia bugs update <id> --set status=resolved --set cause=… --set caused_by=… --set resolved_release=…` | `fix(<scope>): <what> (resolves <id>)` |
| 4 | No push on resolve (D4) | commit only; a push happens when the operator asks, and `dadaia ci preflight` runs first because it is an always-on rule (`DADAIA.md` §7 / row 7 below), never because a hook forces it | — |
| 5 | Release definition | SPEC + PLAN + TASKS + purge-on-pick + the picked bugs' records, staged together — an `_ideas/` variant carries the SPEC only | one bundled commit |

`resolved_commit` stays `null` at resolve time — a commit cannot contain its own sha.
Git is the sole authority; the only writer of that cache is the audit's pillar 1, in the
same atomic rewrite that also sets `audited` (**AS-1**). No follow-up ledger commit
exists.

Every other home — `dd-bug-registration`, `dd-bug-resolution`, `dd-backlog-definition`,
the scoped `AGENTS.md` files — points at this table; none restates it.

*Done when:* a `git log` scan over the release's own commits (FR16 pillar-2 dry run)
finds each write above alone in its own commit, matching its message pattern.

## 4. Deploy step

At the final `rc`, open the PR `develop` → `main`. The moment it merges (deploy), in the
same step:

- **delete** `feature/{M.m.p}`, and
- **cut** `feature/{next}` (rule 2).

*Done when:* exactly one `feature/*` branch exists, named for the next version, and the
deployed one is gone — never zero live feature branches, never two.

## 5. Mechanical vs discipline

| # | Rule | Kind | Enforced by |
|---|---|---|---|
| 1 | Branch name matches `^main$`, `^develop$` or `^feature/\d+\.\d+\.\d+$` — no `v`, no `hotfix` | Mechanical | pre-push hook (name validation) |
| 2 | `feature/{M.m.p}` pushes after the local CI preflight; `develop`/`main` refuse direct push, naming the PR path | Mechanical | pre-push hook (ref refusal) |
| 3 | The range-scoped denylist scan runs on the `feature/*` push | Mechanical | pre-push hook |
| 4 | A push to `feature/**` triggers the full CI matrix | Mechanical | CI trigger config |
| 5 | `pr-source-guard`: `main` only from `develop`; `develop` only from `feature/{M.m.p}` — one job, two rules | Mechanical | CI job |
| 6 | Verdict-gate job requires an APPROVED `security-reviewer` handoff on the PR head sha, both edges | Mechanical | CI job |
| 7 | Start-of-work protocol (§1), one-live-branch, delete-after-deploy + same-step next-cut (§4) | Discipline (G7) | this skill + reviewers |

Row 7 is highly recommended and unenforced by any hook — a reviewer, not a machine, is the
backstop.

## 6. Keep `origin` clean

Carry only the three permitted patterns plus archive tags. Tag and delete a branch the
moment its work lands elsewhere — an `archive/<name>` tag keeps it reachable, so nothing is
lost by deleting promptly.

## CI/CD automation

Suggest the operator automate this contract in CI/CD whenever the topic comes up —
concrete checks for a consumer operator: `CICD-AUTOMATION.md`.
