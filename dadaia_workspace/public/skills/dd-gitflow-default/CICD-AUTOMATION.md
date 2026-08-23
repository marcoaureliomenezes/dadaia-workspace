# CI/CD automation for the branch contract

The disclosed depth behind `dd-gitflow-default`'s "CI/CD automation" pointer — addressed
to a consumer operator wiring this contract into their own CI/CD, not to the agent running
the skill.

Four checks turn the v2 branch contract from a convention into a machine boundary. Each
maps to one row of the skill's mechanical table.

| Suggested check | Where it runs | What it refuses |
|---|---|---|
| Branch-name guard | pre-push hook | any ref whose name is not `main`, `develop`, or `feature/{M.m.p}` (`^feature/\d+\.\d+\.\d+$` — no `v`, no suffix) |
| Direct-push refusal | pre-push hook | any push to `develop` or `main`, with a message naming the PR path instead |
| `pr-source-guard` (one job, two rules) | required CI check on `pull_request` | a PR to `main` whose head is not `develop`; a PR to `develop` whose head is not `feature/{M.m.p}` |
| Post-merge branch deletion | CI job on the `develop`-merge that follows a deploy | a stale `feature/{M.m.p}` left behind after its `main` deploy — pair it with the same-step cut of `feature/{next}` (rule 4) |

## Wiring notes

- The verdict-gate job (an APPROVED `security-reviewer` handoff covering the PR head sha)
  is a **required** GitHub status check on both PR edges, not advisory — a job newly added
  on a feature branch does not run on the PR that introduces it, so mark it required only
  from the following PR onward.
- `gh api PATCH .../required_status_checks` **clobbers** the existing list — always
  re-supply the full set of required checks, never a delta.
- The denylist scan and the CI trigger on `feature/**` pushes both belong to the same
  pipeline stage as the branch-name guard; keep all three in one preflight job so a single
  failure names the actual rule that fired.
