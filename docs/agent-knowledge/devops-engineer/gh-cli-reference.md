# devops-engineer — gh CLI reference

## gh CLI — GitHub Information and Debugging

```bash
# Repository overview
gh repo view --json name,owner,defaultBranch,isPrivate,pushedAt

# List recent workflow runs
gh run list --repo <owner>/<repo> --limit 20
gh run list --workflow=ci.yml --limit 10

# Inspect a specific run
gh run view <run-id>
gh run view <run-id> --log           # full logs
gh run view <run-id> --log-failed    # only failed steps

# Watch a run in real time
gh run watch <run-id>

# Re-run a failed workflow
gh run rerun <run-id> --failed

# List workflow files
gh workflow list

# View a workflow's run history
gh workflow view ci.yml --yaml

# Branch protection
gh api repos/{owner}/{repo}/branches/main/protection
gh api repos/{owner}/{repo}/branches/main/protection/required_status_checks

# Repository secrets (names only — values are never readable)
gh secret list

# Repository variables
gh variable list

# Pull request checks status
gh pr checks <pr-number>

# View PR review status
gh pr view <pr-number> --json reviews,statusCheckRollup

# List environments
gh api repos/{owner}/{repo}/environments

# Check CODEOWNERS
gh api repos/{owner}/{repo}/contents/.github/CODEOWNERS | jq -r '.content' | base64 -d
```

---
