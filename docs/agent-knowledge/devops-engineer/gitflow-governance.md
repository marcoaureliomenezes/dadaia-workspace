---
name: devops-gitflow-governance
description: >
  Protocol for enforcing Git flow branching strategy, branch protection rules, PR review policies,
  CODEOWNERS, and repository governance via GitHub Settings and GitHub Actions. Use when auditing
  a repository's branching discipline, setting up protection rules, or designing a release process.
---

# Git Flow Governance — Protocol

---

## Git Flow — Branch Model

```
main          ← production-only. Protected. Merge via PR from release/* or hotfix/* only.
develop       ← integration branch. Protected. All feature PRs merge here.
feature/*     ← feature/<ticket-id>-short-description  (e.g. feature/PROJ-42-user-auth)
release/*     ← release/v1.2.0  (cut from develop; only bugfixes allowed)
hotfix/*      ← hotfix/v1.2.1-fix-auth-crash  (cut from main; merged to main AND develop)
```

### Commit message convention (Conventional Commits)
```
feat(scope): add user authentication
fix(api): handle null response from payment gateway
docs: update README setup section
chore(deps): bump requests to 2.32.0
ci: add deploy workflow for ECR
refactor(auth): extract token validation to service layer
```

### Merge strategy per branch
| Target | From | Strategy |
|--------|------|----------|
| `main` | `release/*` or `hotfix/*` | Merge commit (preserves release history) |
| `develop` | `feature/*` | Squash merge (clean history per ticket) |
| `release/*` | `develop` | Merge commit |
| `main` AND `develop` | `hotfix/*` | Merge commit to both |

---

## Branch Protection Rules (GitHub Settings → Branches)

### `main` — maximum protection
```
✅ Require a pull request before merging
   ✅ Required approvals: 2
   ✅ Dismiss stale pull request approvals when new commits are pushed
   ✅ Require review from Code Owners

✅ Require status checks to pass before merging
   ✅ Require branches to be up to date
   Required checks: test, lint, security-scan   ← must match exact workflow job names

✅ Require conversation resolution before merging

✅ Require signed commits

✅ Require linear history   OR   Allow merge commits (choose one, document why)

✅ Include administrators   ← no bypass for anyone

✅ Restrict who can push to matching branches
   Allowed: release/*, hotfix/* only

❌ Allow force pushes — NEVER
❌ Allow deletions — NEVER
```

### `develop` — integration protection
```
✅ Require a pull request before merging
   ✅ Required approvals: 1

✅ Require status checks to pass
   Required checks: test, lint

✅ Require branches to be up to date

✅ Allow squash merging (for feature/* PRs)
```

---

## CODEOWNERS (`.github/CODEOWNERS`)

```
# Global fallback — everything requires at least one review from the team
*                           @org/backend-team

# Infrastructure changes require DevOps sign-off
terraform/                  @org/devops-team
.github/                    @org/devops-team
docker/                     @org/devops-team
Dockerfile*                 @org/devops-team

# Secrets and security config
**/secrets*                 @org/security-team
**/auth/                    @org/security-team

# Frontend
frontend/                   @org/frontend-team
*.tsx                       @org/frontend-team
*.css                       @org/frontend-team

# Per-file critical paths
src/core/models.py          @lead-developer
specs/constitution.md       @org/tech-leads
```

**Rule:** Every path that can cause a production incident must have an explicit CODEOWNER.

---

## PR Template (`.github/pull_request_template.md`)

```markdown
## Summary
<!-- What does this PR do? Why? -->

## Type of change
- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] refactor — no behavior change
- [ ] ci — pipeline changes
- [ ] docs — documentation only

## Test plan
- [ ] Unit tests added/updated
- [ ] Integration tests pass locally
- [ ] Manual testing steps: <describe>

## Checklist
- [ ] Follows branch naming convention (`feature/<ticket>-description`)
- [ ] Commit messages follow Conventional Commits
- [ ] No secrets committed
- [ ] CODEOWNERS notified if touching critical paths
- [ ] Breaking changes documented
```

---

## Enforcing Git Flow via GitHub Actions

### Block direct pushes to main/develop
```yaml
# .github/workflows/branch-policy.yml
name: Branch Policy

on:
  push:
    branches: [main, develop]

jobs:
  block-direct-push:
    runs-on: ubuntu-latest
    steps:
      - name: Block direct push
        run: |
          if [[ "${{ github.event_name }}" == "push" ]]; then
            echo "::error::Direct pushes to ${{ github.ref_name }} are not allowed. Use a PR."
            exit 1
          fi
```

### Enforce branch naming
```yaml
# .github/workflows/pr-checks.yml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  branch-name:
    runs-on: ubuntu-latest
    steps:
      - name: Validate branch name
        run: |
          BRANCH="${{ github.head_ref }}"
          PATTERN="^(feature|fix|hotfix|release|chore|docs|ci)/[a-z0-9._-]+$"
          if ! echo "$BRANCH" | grep -qE "$PATTERN"; then
            echo "::error::Branch name '$BRANCH' does not follow naming convention."
            echo "::error::Expected: feature/*, fix/*, hotfix/*, release/*, chore/*, docs/*, ci/*"
            exit 1
          fi
```

### Enforce conventional commits on PR title
```yaml
  commit-message:
    runs-on: ubuntu-latest
    steps:
      - name: Validate PR title (conventional commits)
        run: |
          TITLE="${{ github.event.pull_request.title }}"
          PATTERN="^(feat|fix|docs|style|refactor|test|chore|ci|perf|build|revert)(\([a-z]+\))?: .+"
          if ! echo "$TITLE" | grep -qE "$PATTERN"; then
            echo "::error::PR title does not follow Conventional Commits."
            echo "::error::Expected: feat(scope): description"
            exit 1
          fi
```

---

## Release Automation

### Tag-based release trigger
```yaml
on:
  push:
    tags: ['v*.*.*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Generate changelog
        id: changelog
        run: |
          PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
          if [ -n "$PREV_TAG" ]; then
            CHANGES=$(git log ${PREV_TAG}..HEAD --pretty="- %s (%h)")
          else
            CHANGES=$(git log --pretty="- %s (%h)")
          fi
          echo "changes<<EOF" >> $GITHUB_OUTPUT
          echo "$CHANGES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - uses: softprops/action-gh-release@v2
        with:
          body: ${{ steps.changelog.outputs.changes }}
          generate_release_notes: true
```

---

## Audit Checklist for Existing Repositories

When auditing a repo for Git governance:

```
[ ] Does main have branch protection enabled?
[ ] Are direct pushes to main/develop blocked?
[ ] Are required status checks configured (test, lint at minimum)?
[ ] Are stale review dismissals enabled?
[ ] Is CODEOWNERS present and covering critical paths?
[ ] Is PR template present?
[ ] Is branch naming enforced (via protection or workflow)?
[ ] Is there a release process (tags, changelog)?
[ ] Are secrets stored in GitHub Secrets (not hardcoded)?
[ ] Is signed commits required for main?
[ ] Is force push to main disabled?
```

Any unchecked item is a finding. Report with: location, risk, recommended fix.

---

## References

- GitHub branch protection: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
- CODEOWNERS: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- Conventional Commits: https://www.conventionalcommits.org
- Git Flow: https://nvie.com/posts/a-successful-git-branching-model/
- GitHub Flow (simpler alternative): https://docs.github.com/en/get-started/using-github/github-flow
