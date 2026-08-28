# CI/CD automation for the branch contract

Disclosed depth behind `dd-gitflow-default`'s "CI/CD automation" pointer.
Addressed to a consumer operator wiring this contract into their own CI/CD, not to the agent running the skill.

Four checks turn the v2 branch contract from a convention into a machine boundary. Each maps to one row of the skill's mechanical table.

| Suggested check | Where it runs | What it refuses |
|---|---|---|
| Branch-name guard | pre-push hook | any ref not `main`, `develop`, or `feature/{M.m.p}` (`^feature/\d+\.\d+\.\d+$` — no `v`, no suffix) |
| Direct-push refusal | pre-push hook | any push to `develop`/`main`; message names the PR path instead |
| `pr-source-guard` (1 job, 2 rules) | required CI check | PR to `main` not from `develop`; PR to `develop` not from `feature/{M.m.p}` |
| Post-merge branch deletion | CI job on the `develop`-merge following a deploy | a stale `feature/{M.m.p}` left behind |

## Wiring notes

- The verdict-gate job (an APPROVED `security-reviewer` handoff on the PR head sha) is a required GitHub status check on both PR edges, not advisory.
- A job newly added on a feature branch does not run on the PR that introduces it — mark it required only from the following PR onward.
- `gh api PATCH .../required_status_checks` clobbers the existing list — always re-supply the full set, never a delta.
- The denylist scan and the CI trigger on `feature/**` pushes belong to the same pipeline stage as the branch-name guard.
- Keep all three in one preflight job so a single failure names the actual rule that fired.
