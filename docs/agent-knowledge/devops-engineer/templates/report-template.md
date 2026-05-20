# devops-engineer — Report Templates

This file is referenced from `dadaia_workspace/public/agents/devops-engineer.md`.
It contains the canonical report structure for each mode (AUDIT, SCAN, ONBOARD) and the
standard Secrets/Variables configuration checklist.

---

## Report Structure

### `audit-<timestamp>.md`

```markdown
# DevOps Audit: <Repository>
Date: <ISO 8601>
Repo: <owner>/<repo>
Verdict: GREEN | YELLOW | RED

## Executive Summary
<1 paragraph: overall posture — what works, what's missing, what's at risk>

## Pipeline Inventory
| Workflow | Trigger | Purpose | Status |
|---|---|---|---|
| ci.yml | push, PR | test + lint | OK |
| deploy.yml | push main | ECR + ECS | MISSING |

## Findings

### [CRITICAL] <Title>
Location: <.github/workflows/name.yml:line or GitHub Settings path>
Issue: <precise description>
Risk: <what breaks or gets compromised>
Fix: <exact corrective action — no hedging>

### [HIGH] ...
### [MEDIUM] ...
### [LOW] ...

## Git Flow Compliance
- [ ] main branch protected
- [ ] Force push disabled
- [ ] Required reviews: N
- [ ] Status checks required: [list]
- [ ] CODEOWNERS: present / missing
- [ ] Branch naming enforced: yes / no
- [ ] PR template: present / missing

## Missing Pipelines
List every pipeline that should exist for this project type but doesn't.

## Required Actions (ordered by priority)
1. **<Action>** — <why it's first>
2. ...
```

Verdict:
- **RED** — production can be compromised, or deployments are blocked/broken
- **YELLOW** — governance gaps or manual steps where automation is needed
- **GREEN** — pipelines and governance are solid for this project's size

---

### `scan-<timestamp>.md` (workspace-level inventory)

```markdown
# DevOps Workspace Inventory
Date: <ISO 8601>
Repos scanned: N

## Summary Table
| Repo | Maturity | Security | Workflows | Branches | Terraform |
|---|---|---|---|---|---|
| repo-a | ADVANCED | ✅ OIDC | 7 | 9 | ✅ |
| repo-b | NONE | — | 0 | 1 | ❌ |
| repo-c | BASIC | ❌ CRITICAL: static keys | 2 | 1 | ❌ |

## Per-Repo Snapshot

### <repo-slug> — <Maturity>
**What it is:** [from constitution.md — 1-2 sentences]
**Stack:** [tech stack]
**Security posture:** OIDC ✅ | Static creds ❌ CRITICAL | No cloud deploy —
**Workflows found:** [list with purpose]
**Branches:** [list]
**Terraform / IaC:** yes / no
**Action required:** ONBOARD | IMPROVE | AUDIT | NONE

## Priority Queue (by risk)
1. [CRITICAL] <repo> — static AWS credentials in production workflow
2. [HIGH] <repo> — deployable project with no CI/CD
3. [HIGH] <repo> — deployable project with no CI/CD
4. [MEDIUM] <repo> — CI only, no branch protection
5. [LOW] <repo> — CI only, correct for project type
```

---

### `onboard-<slug>-<timestamp>.md` (per-repo greenfield report)

```markdown
# DevOps Onboard Report — <repo-slug>
Date: <ISO 8601>
Maturity before: <NONE|BASIC>
Target maturity: <STANDARD|ADVANCED>

## What is this project
[From constitution.md — purpose, stack, deploy target, domain. 2-4 sentences.]

## Current State
[What exists today — workflows (list with issues), secrets (static? OIDC?), branches, GitHub config]

## Security Findings

### [CRITICAL] Static AWS credentials  ← (if applicable)
File: .github/workflows/production-deploy.yml:49-50
Issue: `aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}` — static key, violates Security Law.
Risk: Compromised key = full AWS account access. No rotation enforcement.
Fix: Replace with OIDC role (see Step 2 + Step 3 below).
Spec conflict: specs/releases/<active-release>/SPEC.md lists these keys as required — this spec is
wrong. Escalate to product-engineer for correction before closing this report.

## Pipeline Type Decision
Stack detected: [React/Vite/Node.js → S3 + CloudFront]
→ Pipeline type: Web static
Rationale: [why this type fits this project]

## Step-by-Step to Reach Compliance

### Step 1 — GitHub Configuration (Settings → Secrets and variables → Actions)

**Secrets to CREATE:**
- `CLOUDFRONT_DISTRIBUTION_ID` — CloudFront distribution ID from AWS console

**Secrets to DELETE (Security Law violations):**
- `AWS_ACCESS_KEY_ID` — delete after OIDC role is created and tested
- `AWS_SECRET_ACCESS_KEY` — delete after OIDC role is created and tested

**Variables (Settings → Variables → Actions):**
- `AWS_REGION` — e.g. `sa-east-1`
- `S3_BUCKET` — e.g. `marco-menezes.com`

**Environments (Settings → Environments):**
- `production` — required reviewers: @operator; deploy only from main

### Step 2 — AWS IAM Setup (one-time, done by operator with admin access)

```bash
# 1. Create OIDC Identity Provider (once per AWS account)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# 2. Create IAM Role — trust policy restricts to this repo + main branch only
# Save as trust-policy.json:
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:ref:refs/heads/main"
      }
    }
  }]
}

aws iam create-role \
  --role-name github-actions-portifolio-deploy \
  --assume-role-policy-document file://trust-policy.json

# 3. Attach permissions (S3 sync + CloudFront invalidation)
aws iam put-role-policy \
  --role-name github-actions-portifolio-deploy \
  --policy-name deploy-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": ["s3:PutObject","s3:DeleteObject","s3:ListBucket"], "Resource": ["arn:aws:s3:::BUCKET","arn:aws:s3:::BUCKET/*"]},
      {"Effect": "Allow", "Action": "cloudfront:CreateInvalidation", "Resource": "arn:aws:cloudfront::ACCOUNT_ID:distribution/DISTRIBUTION_ID"}
    ]
  }'
```

Note the Role ARN — you will use it in Step 3 as `role-to-assume`.

### Step 3 — Workflow files to create/replace

[Complete YAML workflow — ready to copy-paste, with OIDC, correct job names, environment gate]

### Step 4 — Branch Protection (Settings → Branches → Add rule for `main`)
- Require PR before merging
- Required approvals: 1
- Required status checks: [exact job names from Step 3 workflow]
- Dismiss stale reviews: yes
- Include administrators: yes
- Disable force push: yes

## Verification checklist
After setup, confirm each item before closing this report:
- [ ] Old static secrets deleted from GitHub Settings
- [ ] OIDC Identity Provider created in AWS IAM
- [ ] IAM Role created with correct trust policy (repo-scoped)
- [ ] New workflow pushed and triggered: `gh run watch <run-id>`
- [ ] Deploy job assumes role successfully (no static key errors)
- [ ] Branch protection active — PR required before merge
- [ ] PR CI check passes before merge is allowed
- [ ] Deploy triggered only on merge to main, not on PR open
```

---

## Secrets and Variables Checklist

When creating a new pipeline, always output this before the workflow YAML:

```markdown
## Required GitHub Configuration

### Secrets (Settings → Secrets and variables → Actions → Secrets)
- `SECRET_NAME` — what it is and where to get it

### Variables (Settings → Secrets and variables → Actions → Variables)
- `VAR_NAME` — example value and purpose

### Environments (Settings → Environments)
- `staging` — no required reviewers; auto-deploy on merge to develop
- `production` — required reviewers: @team-lead; deploy on merge to main

### Branch Protection (Settings → Branches → Add rule for `main`)
- Require PR before merging
- Required approvals: 1
- Required status checks: [list exact job names from the workflow]
- Dismiss stale reviews: yes
- Include administrators: yes
- Disable force push: yes
```

---
