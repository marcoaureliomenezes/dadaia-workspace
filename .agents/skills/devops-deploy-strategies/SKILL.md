---
name: devops-deploy-strategies
description: >
  Deployment reference and protocols for the four main artifact types: Docker images to ECR,
  Python packages to PyPI/private registries, Web applications (S3+CloudFront, ECS, EC2), and
  Terraform infrastructure. Covers deployment patterns (blue/green, canary, rolling), rollback
  procedures, and AWS integration via OIDC. Use when building or auditing any deployment pipeline.
---

# Deploy Strategies — Reference and Protocol

---

## 1. Docker Images → Amazon ECR

### Full workflow: build, tag, scan, push
```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    tags: ['v*.*.*']

permissions:
  id-token: write
  contents: read

jobs:
  build-push:
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}
      image_digest: ${{ steps.push.outputs.digest }}

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Login to ECR
        id: ecr-login
        uses: aws-actions/amazon-ecr-login@v2

      - name: Generate image metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.ecr-login.outputs.registry }}/${{ vars.ECR_REPOSITORY }}
          tags: |
            type=ref,event=branch
            type=ref,event=tag
            type=sha,prefix=sha-,format=short

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push
        id: push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Scan image for vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.meta.outputs.tags }}
          format: sarif
          exit-code: '1'
          severity: CRITICAL,HIGH
```

### ECR lifecycle policy (prevent unbounded image accumulation)
```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 tagged releases",
      "selection": { "tagStatus": "tagged", "tagPrefixList": ["v"], "countType": "imageCountMoreThan", "countNumber": 10 },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 2,
      "description": "Expire untagged images after 7 days",
      "selection": { "tagStatus": "untagged", "countType": "sinceImagePushed", "countUnit": "days", "countNumber": 7 },
      "action": { "type": "expire" }
    }
  ]
}
```

---

## 2. Python Packages

### Publish to PyPI
```yaml
name: Publish Python Package

on:
  push:
    tags: ['v*.*.*']

permissions:
  id-token: write   # for PyPI trusted publishing (no API token needed)
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi-release    # environment gate for manual approval

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install build tools
        run: pip install build

      - name: Build distribution
        run: python -m build

      - name: Publish to PyPI (trusted publishing)
        uses: pypa/gh-action-pypi-publish@release/v1
        # No API_TOKEN needed — uses OIDC trusted publishing
```

### Publish to private registry (AWS CodeArtifact)
```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Get CodeArtifact token
        run: |
          TOKEN=$(aws codeartifact get-authorization-token \
            --domain ${{ vars.CODEARTIFACT_DOMAIN }} \
            --domain-owner ${{ vars.AWS_ACCOUNT_ID }} \
            --query authorizationToken --output text)
          echo "CODEARTIFACT_TOKEN=$TOKEN" >> $GITHUB_ENV

      - name: Publish to CodeArtifact
        run: |
          pip install twine
          twine upload \
            --repository-url https://${{ vars.CODEARTIFACT_DOMAIN }}-${{ vars.AWS_ACCOUNT_ID }}.d.codeartifact.us-east-1.amazonaws.com/pypi/${{ vars.CODEARTIFACT_REPO }}/legacy/ \
            --username aws \
            --password ${{ env.CODEARTIFACT_TOKEN }} \
            dist/*
```

---

## 3. Web Applications

### Static site → S3 + CloudFront
```yaml
jobs:
  deploy-static:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build frontend
        run: npm ci && npm run build
        env:
          VITE_API_URL: ${{ vars.API_URL }}

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Sync to S3
        run: |
          aws s3 sync dist/ s3://${{ vars.S3_BUCKET }} \
            --delete \
            --cache-control "public, max-age=31536000, immutable" \
            --exclude "index.html"
          # index.html must not be cached
          aws s3 cp dist/index.html s3://${{ vars.S3_BUCKET }}/index.html \
            --cache-control "no-cache, no-store, must-revalidate"

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

### ECS (Fargate) — rolling update
```yaml
jobs:
  deploy-ecs:
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Download current task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition ${{ vars.ECS_TASK_FAMILY }} \
            --query taskDefinition > task-def.json

      - name: Update image in task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-def.json
          container-name: ${{ vars.CONTAINER_NAME }}
          image: ${{ needs.build.outputs.image_tag }}

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ vars.ECS_SERVICE }}
          cluster: ${{ vars.ECS_CLUSTER }}
          wait-for-service-stability: true
          wait-for-minutes: 10
```

---

## 4. Terraform Infrastructure

### Plan on PR, Apply on merge
```yaml
name: Terraform

on:
  pull_request:
    paths: ['terraform/**']
  push:
    branches: [main]
    paths: ['terraform/**']

permissions:
  id-token: write
  contents: read
  pull-requests: write   # to comment plan output on PR

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: terraform/

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: '1.7.0'

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Terraform Init
        run: terraform init -backend-config="bucket=${{ vars.TF_STATE_BUCKET }}"

      - name: Terraform Format Check
        run: terraform fmt -check -recursive

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Plan
        id: plan
        run: |
          terraform plan -no-color -out=tfplan 2>&1 | tee plan_output.txt
          echo "plan_output<<EOF" >> $GITHUB_OUTPUT
          cat plan_output.txt >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - name: Comment plan on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '```hcl\n${{ steps.plan.outputs.plan_output }}\n```'
            })

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve tfplan
```

### Terraform state — remote backend (S3 + DynamoDB locking)
```hcl
terraform {
  backend "s3" {
    bucket         = "my-company-tf-state"
    key            = "services/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

---

## Deployment Patterns

### Blue/Green (zero-downtime swap)
```
1. Deploy new version as "green" (separate ECS service or target group)
2. Run smoke tests against green
3. Shift 100% traffic from blue to green (ALB listener rule update)
4. Monitor for 10 minutes
5. Terminate blue if healthy; rollback (restore listener rule) if not
```

### Canary (gradual traffic shift)
```
1. Deploy new version alongside current
2. Route 5% of traffic to canary (ALB weighted target groups)
3. Monitor error rate and latency for 15 minutes
4. Increment: 5% → 20% → 50% → 100% (or auto via CodeDeploy)
5. Abort and rollback if error rate exceeds threshold
```

### Rolling update (ECS default)
```
ECS replaces tasks gradually:
- minimumHealthyPercent: 100  ← never reduce capacity below 100%
- maximumPercent: 200          ← allow up to double tasks during rollout
```

---

## Rollback Procedures

### Docker/ECS rollback
```bash
# Get previous task definition revision
PREV_REVISION=$(aws ecs describe-services \
  --cluster $CLUSTER --services $SERVICE \
  --query 'services[0].deployments[-1].taskDefinition' --output text)

# Force deploy with previous revision
aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --task-definition $PREV_REVISION \
  --force-new-deployment
```

### Terraform rollback
```bash
# Revert to previous state version in S3
aws s3 cp s3://tf-state-bucket/services/prod/terraform.tfstate.backup \
          s3://tf-state-bucket/services/prod/terraform.tfstate

# Re-apply previous version
terraform apply -auto-approve
```

### Static site rollback
```bash
# Re-sync previous build artifact from S3 versioning
aws s3api list-object-versions --bucket $BUCKET --prefix index.html
aws s3api get-object --bucket $BUCKET --key index.html \
  --version-id $PREV_VERSION index.html
aws s3 cp index.html s3://$BUCKET/index.html
aws cloudfront create-invalidation --distribution-id $CF_ID --paths "/*"
```

---

## Security Checklist for Deployments

```
[ ] AWS credentials use OIDC — no static keys in secrets
[ ] ECR images scanned for CRITICAL/HIGH CVEs before deploy
[ ] Terraform plan reviewed on PR before apply
[ ] Deployment to production requires environment gate (manual approval)
[ ] Terraform state bucket has versioning and server-side encryption enabled
[ ] DynamoDB table used for Terraform state locking
[ ] Docker images built with non-root USER in Dockerfile
[ ] Secrets injected via env — never baked into image
[ ] CloudFront uses HTTPS only (redirect HTTP → HTTPS)
[ ] S3 bucket blocks all public access (served only via CloudFront OAC)
```

---

## References

- AWS ECR: https://docs.aws.amazon.com/ecr/
- ECS Deploy action: https://github.com/aws-actions/amazon-ecs-deploy-task-definition
- Terraform GitHub Actions: https://developer.hashicorp.com/terraform/tutorials/automation/github-actions
- PyPI Trusted Publishing: https://docs.pypi.org/trusted-publishers/
- AWS CodeDeploy Blue/Green: https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html
