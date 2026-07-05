---
name: github-actions-cicd
description: >
  Use this skill when authoring or reviewing CI/CD — GitHub Actions workflows,
  gitflow branch model, release/deploy gates, and container/deploy config.
  Carries the job-graph, least-privilege permissions, action/image pinning,
  secret-handling, and deploy-gate checklist. Shipped by the devops plugin pack;
  owned by devops-engineer.
---

# Skill: github-actions-cicd

The pipeline-authoring craft protocol for the `devops` pack. `devops-engineer` uses it to build
and review CI/CD that builds, tests, gates, and ships a repo. Reach for it at the start of every
CI/CD task.

## When to use

- Authoring or changing a GitHub Actions workflow (build, test, lint, release, deploy).
- Wiring the gitflow branch model and release/deploy gates into CI.
- Reviewing a pipeline change for least-privilege, pinning, secret handling, and deploy safety.

## 1. Job graph

- One workflow per concern (CI, release, deploy); jobs with explicit `needs:` edges — fail fast,
  no hidden ordering.
- Trigger precisely: `on:` scoped to the branches/paths that matter; avoid re-running the world
  on every push.
- Cache deterministically — key on the lockfile hash; never a floating cache key.
- Matrix only what genuinely varies (OS, language version); do not matrix for its own sake.

## 2. Least-privilege permissions (the default that bites)

| Rule | Detail |
|---|---|
| Explicit `permissions:` | Set at workflow or job level; start from `contents: read`. |
| No `write-all` | Grant only the scopes a job needs (e.g. `packages: write` for a publish job). |
| `GITHUB_TOKEN` scope | Narrow it per job; a test job needs no write. |
| Forked-PR safety | `pull_request` from forks runs without secrets — never expose secrets to it; use `pull_request_target` only with extreme care and no untrusted checkout. |

## 3. Supply-chain pinning

- Pin third-party actions to a full **commit sha**, not a floating tag (`@v4` is mutable).
- Pin container base images by digest; rebuild deliberately, not implicitly.
- Checksum/verify downloaded artifacts and tool installers.

## 4. Secret handling

- Secrets only via `secrets.*` / environment secret stores — never hardcoded, never echoed,
  never written to logs or step outputs.
- Gate deploy jobs on GitHub `environments` with required reviewers and, where available,
  wait timers.
- Rotate on exposure; a secret printed to a log is a leaked secret.

## 5. Gitflow + release/deploy gates

- Honour `release-governance`: a release matures on a single `feature/{version}` branch through
  `alpha-N`/`rc-N`; the pre-push CI-preflight and security-verdict chokepoints gate the push.
  Encode the gate ladder in CI — never author a path that bypasses it.
- Deploy only on green CI **and** the required approvals; define health checks and a rollback
  path. Reproducible, deterministic builds — no "works on this runner" surprises.

## 6. Boundary with the workspace's own CI gate

The dadaia workspace ships its **own** pre-push CI gate shell asset
(`public/scripts/pre-push-ci-gate.sh`) — that asset is part of the AI-entity surface and is
owned by `ai-engineer`, not this pack. This skill authors CI/CD for the **consumer repos** under
`repos/<slug>/` (their `.github/workflows/**`, container, and deploy config). Do not edit the
workspace's own `public/scripts/**`.

## 7. Security checklist (OWASP-aligned)

| # | Check |
|---|---|
| A02 | No secret hardcoded/echoed/logged. |
| A04 | Least-privilege `permissions:`; deploy gated on reviewers. |
| A05 | Base images + actions pinned; outdated pins flagged. |
| A08 | Supply-chain integrity (sha-pinned actions, checksummed artifacts). |
| A09 | Forked-PR workflows cannot reach secrets; security events logged. |
| A10 | Deploy targets from an allowlist, never an arbitrary endpoint. |

## Guardrails

| Rule | Detail |
|---|---|
| No application code | Code under test belongs to `software-engineer` / `frontend-engineer`. |
| No E2E ownership | The E2E suite belongs to `qa-engineer`; you wire it into CI, you do not author it. |
| No workspace self-CI | `public/scripts/**` is `ai-engineer`'s; this pack targets consumer-repo CI. |
| Privileged review | Secret/permission/deploy changes pair with `security-reviewer`; the push is chokepoint-gated regardless. |
| Handoff | Emit handoff JSON via `dadaia-handoff-emitter` under `.dadaia/handoff/<context>/` after the task. |
