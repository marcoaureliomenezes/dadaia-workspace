---
name: github-actions-pipelines
description: >
  Complete reference and authoring protocol for GitHub Actions workflows. Covers workflow anatomy,
  triggers, jobs, steps, matrix builds, caching, artifacts, reusable workflows, OIDC authentication,
  secrets management, and environment protection. Use when creating, reviewing, or debugging any
  .github/workflows/*.yml file.
---

# GitHub Actions Pipelines — Reference and Authoring Protocol

---

## Workflow Anatomy

```yaml
name: <workflow-name>

on: <trigger>          # when to run
  
env:                   # workflow-level env vars
  KEY: value

jobs:
  <job-id>:
    runs-on: ubuntu-latest
    environment: <env-name>   # optional: gates on environment protection
    needs: [<other-job>]      # dependency chain
    if: <condition>
    
    steps:
      - uses: actions/checkout@v4
      - name: <step-name>
        run: <shell command>
        env:
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
```

---

## Triggers (on:)

### Push / Pull Request
```yaml
on:
  push:
    branches: [main, develop]
    tags: ['v*.*.*']
    paths: ['src/**', 'pyproject.toml']    # run only when these paths change
  pull_request:
    branches: [main, develop]
    types: [opened, synchronize, reopened]
```

### Manual + Scheduled
```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options: [staging, production]
      dry_run:
        type: boolean
        default: false
  schedule:
    - cron: '0 6 * * 1-5'    # weekdays at 06:00 UTC
```

### Workflow Call (reusable)
```yaml
on:
  workflow_call:
    inputs:
      image_tag:
        required: true
        type: string
    secrets:
      AWS_ROLE_ARN:
        required: true
```

---

## Jobs — Patterns

### Sequential pipeline
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps: [...]

  build:
    needs: test           # only runs if test passes
    runs-on: ubuntu-latest
    steps: [...]

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps: [...]
```

### Matrix build (multi-version, multi-OS)
```yaml
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.10', '3.11', '3.12']
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
```

### Conditional jobs
```yaml
jobs:
  deploy-prod:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    ...
  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    ...
```

---

## Secrets and Environment Variables

### Secret access
```yaml
steps:
  - name: Deploy
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      API_KEY: ${{ secrets.API_KEY }}
    run: ./deploy.sh
```

### Environment secrets (scoped per environment)
```yaml
jobs:
  deploy:
    environment: production    # gates on environment approval + uses env-scoped secrets
    steps:
      - run: echo ${{ secrets.PROD_API_KEY }}
```

### Secret masking — never echo secrets directly
```bash
# BAD — leaks value in logs
echo "API_KEY=${{ secrets.API_KEY }}"

# GOOD — mask via env
env:
  API_KEY: ${{ secrets.API_KEY }}
run: ./script.sh    # script reads $API_KEY from env
```

### Variable inheritance (precedence: step > job > workflow > org/repo)
```yaml
env:
  REGION: us-east-1           # workflow level

jobs:
  deploy:
    env:
      ENV_NAME: production    # job level — overrides workflow
    steps:
      - env:
          EXTRA: value        # step level — overrides job
        run: ...
```

### GitHub Actions variables (vars context — non-sensitive)
```yaml
run: echo ${{ vars.APP_VERSION }}   # set in Settings > Variables
```

---

## Caching

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      .venv
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml', '**/poetry.lock') }}
    restore-keys: |
      ${{ runner.os }}-pip-

# For Node
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

**Rule:** Always hash the lockfile/requirements file, not the source. A cache hit on a stale lockfile causes non-deterministic builds.

---

## Artifacts

```yaml
# Upload
- uses: actions/upload-artifact@v4
  with:
    name: dist-${{ github.sha }}
    path: dist/
    retention-days: 7

# Download in a later job
- uses: actions/download-artifact@v4
  with:
    name: dist-${{ github.sha }}
    path: dist/
```

---

## OIDC — AWS Authentication (no static keys)

**Always prefer OIDC over static AWS keys stored as secrets.**

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
      aws-region: us-east-1
      role-session-name: GitHubActions-${{ github.run_id }}
```

AWS IAM Trust Policy (set on the role):
```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::<ACCOUNT>:oidc-provider/token.actions.githubusercontent.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:<org>/<repo>:ref:refs/heads/main"
    }
  }
}
```

---

## Reusable Workflows

Caller:
```yaml
jobs:
  deploy:
    uses: ./.github/workflows/deploy-image.yml@main
    with:
      image_tag: ${{ needs.build.outputs.image_tag }}
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
```

Callee (`.github/workflows/deploy-image.yml`):
```yaml
on:
  workflow_call:
    inputs:
      image_tag: { required: true, type: string }
    secrets:
      AWS_ROLE_ARN: { required: true }

jobs:
  deploy:
    ...
```

---

## Composite Actions (`.github/actions/<name>/action.yml`)

```yaml
name: Setup Python venv
description: Install deps and cache
inputs:
  python-version:
    default: '3.11'
runs:
  using: composite
  steps:
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}
    - uses: actions/cache@v4
      with:
        path: .venv
        key: venv-${{ hashFiles('poetry.lock') }}
    - shell: bash
      run: pip install poetry && poetry install
```

Usage: `uses: ./.github/actions/setup-python`

---

## Job Outputs

```yaml
jobs:
  build:
    outputs:
      image_tag: ${{ steps.tag.outputs.value }}
    steps:
      - id: tag
        run: echo "value=sha-${GITHUB_SHA::7}" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    steps:
      - run: echo "Deploying ${{ needs.build.outputs.image_tag }}"
```

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| `actions/checkout` without `fetch-depth: 0` | Tags and git history missing — use `fetch-depth: 0` for semantic release |
| Static AWS keys in secrets | Replace with OIDC role assumption |
| Cache key not including lockfile hash | Stale deps — always hash the lockfile |
| Hardcoding `ubuntu-latest` for production | Pin to `ubuntu-24.04` to avoid unexpected runner upgrades |
| `if: always()` on deploy step | Deploys even when tests fail — use `if: success()` |
| `pull_request` trigger on forks | Secrets not available to fork PRs — use `pull_request_target` carefully (security risk) |
| `workflow_dispatch` without environment gate | Manual deploys bypass protection rules |

---

## References

- GitHub Actions docs: https://docs.github.com/en/actions
- `actions/checkout@v4`, `actions/cache@v4`, `actions/upload-artifact@v4`
- `aws-actions/configure-aws-credentials@v4`
- GitHub OIDC: https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
