# CI/CD automation for the branch contract

Disclosed depth behind `dd-gitflow-default`'s "CI/CD automation" pointer.
Addressed to a consumer operator wiring this contract into their own CI/CD, not to the agent running the skill.

Four checks turn the branch contract from a convention into a machine boundary. Each maps to one row of the skill's mechanical table; branch names are the `gitflow:` keys of `specs/constitution.md`.

| Suggested check | Where it runs | What it refuses |
|---|---|---|
| Branch-name guard | pre-push hook | any ref not the principal, the integration branch, or `<work>M.m.p` (numeric `M.m.p` — no `v`, no suffix) |
| Direct-push refusal | pre-push hook | any push to the integration or principal branch; message names the PR path instead |
| `pr-source-guard` (1 job, 2 rules) | required CI check | PR to `principal` not from `integration` or the release-please release PR; PR to `integration` not from `<work>M.m.p` |
| Post-merge branch deletion | CI job on the integration merge following a deploy | a stale work branch left behind |

## Wiring notes

- No CI job calls a model API; the security review is the `dd-code-reviewer` lens run before the PR.
- A job newly added on a feature branch does not run on the PR that introduces it — mark it required only from the following PR onward.
- `gh api PATCH .../required_status_checks` clobbers the existing list — always re-supply the full set, never a delta.
- The denylist scan and the CI trigger on `<work>**` pushes belong to the same pipeline stage as the branch-name guard.
- Keep all three in one preflight job so a single failure names the actual rule that fired.
