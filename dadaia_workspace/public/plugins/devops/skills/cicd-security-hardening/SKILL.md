---
name: cicd-security-hardening
description: >
  Use this skill when hardening a CI/CD pipeline's security posture —
  SHA-pinning actions, least-privilege workflow permissions and tokens, secret
  hygiene, untrusted-input isolation, and supply-chain integrity. Carries the
  pipeline threat-model and hardening checklist. Shipped by the devops plugin
  pack; owned by devops-engineer.
---

# Skill: cicd-security-hardening

The pipeline-security protocol for the `devops` pack. `devops-engineer` uses it to harden —
or review — the security posture of CI/CD. Where `github-actions-cicd` covers pipeline
*authoring* (job graph, gates, baseline security), this skill is the dedicated hardening
pass: the threat model and the checklist applied when a pipeline touches secrets,
credentials, deploy targets, or untrusted input.

## When to use

- A security-hardening pass over an existing pipeline.
- Any workflow change that adds a secret, a permission scope, a third-party action, or a
  deploy credential.
- Reviewing untrusted-input surfaces (forked PRs, issue/PR titles and bodies, external
  artifacts) reaching workflow code.

## 1. Threat model — what a pipeline compromise buys

A CI pipeline is an execution environment holding credentials. Treat every job as a
potential attacker foothold and ask, per job: what can this job read (secrets, tokens),
write (repo, registry, deploy target), and who can make it run (push, fork PR, schedule)?
The hardening below shrinks each of those three axes.

## 2. Pin the supply chain (SHA-pinning)

| Rule | Detail |
|---|---|
| Full-commit-SHA pins | Every third-party action pinned to a full commit sha with a version comment — a floating tag (`@v4`) or branch ref is mutable and hijackable. |
| Pin everything executed | Actions, container base images (by digest), tool installers, and downloaded scripts — checksum-verify anything fetched at run time. |
| Deliberate upgrades | Pins move via reviewed PRs (bot-assisted is fine); an upgrade diff shows old sha → new sha, never "bumped stuff". |
| No `curl \| sh` | Unverified pipe-to-shell installers are an unauditable execution of remote code. |

## 3. Least-privilege permissions and tokens

| Rule | Detail |
|---|---|
| Explicit `permissions:` | Top-level default `contents: read` (or none); each job adds only what it needs. Absent = inherited = usually too much. |
| No `write-all` | A blanket write token turns any compromised step into a repo-write primitive. |
| Job-scoped escalation | Only the publish job gets `packages: write`; only the release job gets `contents: write`. Test jobs write nothing. |
| Short-lived cloud creds | Prefer OIDC federation over long-lived cloud keys stored as secrets; scope the federated role to the minimum. |
| Environment gates | Deploy credentials live in deployment environments with required reviewers — not as repo-wide secrets any job can read. |

## 4. Secret hygiene

- Secrets flow only through the platform secret store; never hardcoded, never in workflow
  files, never in artifacts or caches.
- Never echo, log, or write a secret to a step output/summary — masking is best-effort, not
  a guarantee; a logged secret is a rotated secret.
- Scope each secret to the narrowest environment/job; audit and prune unused secrets.
- Rotate on any suspicion of exposure; treat rotation as routine, not exceptional.

## 5. Untrusted input isolation

| Surface | Rule |
|---|---|
| Forked PRs | Run without secrets (`pull_request`); `pull_request_target` only with no checkout of untrusted code and extreme review. |
| Script injection | Never interpolate untrusted strings (PR titles, branch names, issue bodies) into `run:` shell — pass them through env vars and quote. |
| External artifacts | Artifacts from an untrusted or cross-workflow source are data, not code — verify before executing anything from them. |
| Cache poisoning | Caches are writable by the branch that created them; never let an untrusted branch's cache feed a privileged job. |

## 6. Integrity and detection

- Protect the workflow files themselves: changes to `.github/workflows/**` require review
  (they are privileged code).
- Emit and keep audit trails: who triggered what, with which ref and sha; alert on
  first-use of a new action or a permission widening.
- Sign or attest built artifacts where the toolchain supports it, so deploy targets can
  verify provenance (build-once/promote from `container-build-and-deploy` composes here).

## Guardrails

| Rule | Detail |
|---|---|
| Authoring baseline elsewhere | Job graph and pipeline structure live in `github-actions-cicd`; this skill is the hardening pass over them. |
| Generic content | This checklist is platform-practice, not workspace policy; the workspace's own push gates are governed by `release-governance`. |
| Always pair | Every change in this skill's domain (secrets, permissions, pins, deploy creds) pairs with `security-reviewer` — no solo hardening merges. |
| No application code | Vulnerable code found under test routes to `software-engineer` via PM. |
| Handoff | Emit handoff JSON via `dadaia-handoff-emitter` under `.dadaia/handoff/<context>/` after the task. |
