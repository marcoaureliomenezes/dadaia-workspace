---
name: container-build-and-deploy
description: >
  Use this skill when authoring container build or deploy config — Dockerfiles,
  multi-stage builds, compose files, image tagging/registries, and deploy
  rollout/rollback strategy. Carries the image-hygiene, build-determinism,
  registry, and rollout checklist. Shipped by the devops plugin pack; owned by
  devops-engineer.
---

# Skill: container-build-and-deploy

The container craft protocol for the `devops` pack. `devops-engineer` uses it when the task
is a `Dockerfile`, a compose file, or deploy config under a repo's deploy tree. The CI jobs
that build and push these images live in the `github-actions-cicd` skill's domain; this
skill owns what the image and the rollout *are*.

## When to use

- Writing or reviewing a `Dockerfile` / `*.Dockerfile` / `docker-compose*.yml`.
- Defining image tagging, registry, and promotion strategy.
- Designing a deploy rollout (and its rollback path) in `deploy/**` config.

## 1. Image build hygiene

| Rule | Detail |
|---|---|
| Minimal, pinned base | Smallest base that runs the workload (slim/alpine/distroless where viable), pinned by digest — a floating `latest` base is an unreproducible build. |
| Multi-stage always | Build tools, compilers, and dev dependencies live in builder stages; the runtime stage carries only the artifact and its runtime deps. |
| Non-root runtime | Create and switch to an unprivileged user; a root container is a finding. |
| No secrets in layers | Never `COPY`/`ARG`/`ENV` a secret — deleted-in-a-later-layer is still in the image history. Inject at runtime (env/secret store) or use build-secret mounts. |
| Deterministic layers | Order instructions least- to most-frequently-changing; copy lockfiles and install dependencies before copying source, so dependency layers cache. |
| `.dockerignore` | Exclude VCS metadata, local caches, test artifacts, and anything not needed to build — smaller context, no accidental leaks. |
| Healthcheck + signals | Define a healthcheck; run the process as PID 1 with proper signal handling (or an init shim) so stops are graceful. |

## 2. Compose discipline

- Compose files describe topology (services, networks, volumes, dependencies) — configuration
  values come from env files or the environment, not hardcoded per-service.
- One canonical base compose file; environment deltas as override files, never a forked copy
  per environment.
- Named volumes for state; bind mounts only for local development, never in a deploy compose.
- `depends_on` expresses start order, not readiness — gate on healthchecks for readiness.

## 3. Tagging, registries, promotion

| Rule | Detail |
|---|---|
| Immutable tags | Tag images with the version and/or the git sha; never re-push a moved tag. `latest` is a convenience alias at most, never a deploy reference. |
| Deploy by digest | Deploy config references version tags or digests — a deploy that says `latest` is undeployable history. |
| Build once, promote | The image promoted to production is byte-identical to the one tested; promotion re-tags, it never rebuilds. |
| Registry hygiene | Scan images for known vulnerabilities before promotion; expire untagged/stale images by policy. |
| Least-privilege push | CI credentials can push only the repo's own image namespace. |

## 4. Deploy rollout and rollback

- **Health-gated rollout:** new instances must pass health/readiness checks before receiving
  traffic; a rollout with no health gate is an outage with extra steps.
- **Rollback is config, not heroics:** the previous known-good image reference stays
  deployable; rolling back is re-applying it — documented, tested, and fast.
- **Strategy fits the workload:** rolling update for stateless services; recreate only when
  the workload cannot run two versions; stateful migrations are sequenced explicitly
  (expand → migrate → contract), never "deploy and hope".
- **Config/schema compatibility:** a new image must tolerate the old config/schema for the
  duration of the rollout window.
- **Observability at the seam:** deploy events, versions, and health transitions are logged;
  a silent deploy is undiagnosable.

## Guardrails

| Rule | Detail |
|---|---|
| CI jobs elsewhere | The workflow that builds/pushes/deploys lives in `github-actions-cicd`; this skill owns image and rollout content. |
| No application code | The service inside the container belongs to `software-engineer` / `frontend-engineer`. |
| No secrets baked | Secrets never enter image layers, compose files, or deploy config in the repo — runtime injection only. |
| Privileged review | Registry credentials, deploy targets, and rollout changes pair with `security-reviewer`. |
| Handoff | Emit handoff JSON via `dadaia-handoff-emitter` under `.dadaia/handoff/<context>/` after the task. |
