---
name: dadaia-gitflow
description: >
  Use whenever git is used — branching, committing, merging, pushing, opening a PR,
  cutting a hotfix, or minting a version. The single operational home of the
  workspace's four-branch model: which branch each SDD stage runs on, when it
  commits, where it merges, and when it pushes. `DADAIA.md` states the law once;
  this skill is where the law operates.
---

# dadaia-gitflow — The Branch Contract

## The four branches — no fifth

| Pattern | Lives | Pushable | Cut from | Merges into |
|---|---|---|---|---|
| `main` | remote + local | **No** — never committed or pushed to directly | — | receives PRs from `develop` only |
| `develop` | remote + local | **Yes — the only pushable branch** | `main` (one-time bootstrap) | `main` (via PR, GitHub-enforced) |
| `feature/{M.m.p}` | **local only** | No | `develop` | `develop`, at two milestones (below) |
| `hotfix/{M.m.p}` | **local only** | No | `develop` | `develop`, at fix completion |

`main` advances only through a PR whose head is `develop` — enforced by the
`pr-source-guard` required check, not by convention.

## Stage contract — one row per SDD-flow stage

| Stage | Branch | Commit cadence | Merge target | Push trigger |
|---|---|---|---|---|
| backlog-definition | `develop` | one commit per entry authored/sanitized | — (already `develop`) | none dedicated — rides the next `develop` push |
| bug-register | `develop` | one commit per `reported` event | — (already `develop`) | none dedicated — rides the next `develop` push |
| bug-fix/hotfix | `hotfix/{M.m.p}` | one commit at GREEN (fix + RED-turned-green test) | `develop`, mints the PATCH at merge | rides the next `develop` push |
| release-definition | `feature/{M.m.p}` | as SPEC/PLAN/TASKS are authored | `develop` — **milestone (a)**, when the trio is `Aprovado` | milestone (a): mandatory, see below |
| release-implementation | `feature/{M.m.p}` | one commit per completed task group | `develop` — **milestone (b)**, at ship | milestone (b): mandatory, see below |
| ship | `develop` (post-merge) | — (no new commits; PR + merge only) | `main`, via PR from `develop` | milestone (b)'s `develop` push, then the PR |
| closure/archive | `develop` | one commit for memory + CLOSURE + archive | — (already `develop`) | rides the next `develop` push |

Every stage lands on exactly one branch. `feature/*` is the only branch that carries
both definition and implementation — it is not implementation-only.

## The two merge milestones

`feature/{M.m.p}` merges into local `develop` exactly twice:

- **(a) definition** — when SPEC + PLAN + TASKS are all `Aprovado`.
- **(b) ship** — at release ship.

Each merge is followed, **in this exact order**, by two mandatory steps:

1. a **diff-based security review** of `origin/develop..develop` — the delta about to
   be pushed, nothing wider;
2. **push `develop`**.

A release defined and reviewed is therefore committed and pushed the moment
milestone (a) clears — implementation never starts on an unreviewed, unpushed
definition.

## Hotfix: PATCH-mint, no ceremony

A bug fix stays Arm B in full — register, reproduce, RED, root-cause fix, GREEN,
`resolved` event, commit — now run on `hotfix/{M.m.p}` where the version is the
**next PATCH**. At merge into `develop`, in the **same commit**:

- bump `pyproject.toml`'s version to the minted PATCH;
- add the `CHANGELOG.md` entry.

**No release ceremony.** No SPEC, no PLAN, no TASKS, no `specs/releases/<id>/`
directory. The bug ledger plus the `CHANGELOG.md` entry are the record.

## Mechanical vs discipline

Three mechanisms actually refuse or fail a violation — everything else is caught by
review, not by a machine:

| # | Mechanism | Refuses |
|---|---|---|
| 1 | pre-push ref refusal | any pushed ref other than `refs/heads/develop` (tag pushes keep their carve-out) |
| 2 | branch-name validation | a branch name outside the four permitted patterns, at push-attempt time |
| 3 | `pr-source-guard` (GitHub required check) | a PR to `main` whose head is not `develop` |

Everything else — commit cadence, task-group grouping, the definition-before-
implementation order, closure ordering, backlog sanitization — is discipline: this
skill and `DADAIA.md` §5/§6 are the record, and reviewers are the backstop. No hook
reads a commit message or a task marker.

## See also

`DADAIA.md` §5/§6 states the law this skill operates; `dadaia-task-manager` for
task-marker discipline; `dadaia-release-definition` and `dadaia-release-closure` for
the definition/closure protocols that ride these branches.
