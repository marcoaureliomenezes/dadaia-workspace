# devops-engineer — Tooling Reference

## Tooling Reference

```bash
# Discover workflows in current repo
find .github -name "*.yml" | sort

# Scan for static credential violations across all repos
grep -rn "AWS_ACCESS_KEY_ID\|AWS_SECRET_ACCESS_KEY" repos/*/`.github`/ 2>/dev/null

# Scan secrets/vars referenced in workflows
grep -rn "secrets\.\|vars\." .github/workflows/

# Validate YAML
.dadaia/.venv/bin/python -c "import yaml; yaml.safe_load(open('FILE'))"

# Check branch protection
gh api repos/{owner}/{repo}/branches/{branch}/protection

# Full repo DevOps snapshot
gh repo view --json name,owner,defaultBranch,isPrivate
gh workflow list
gh run list --limit 5
gh secret list
gh variable list
```
