---
title: Hermes and dadaia-workspace integration audit
date: 2026-07-15
status: remediation-required
target_release: v0.2.5
---

# Hermes and dadaia-workspace integration audit

## Verdict

The assembled Hermes consumer journey is not release-safe even though the
provider's isolated test suites are substantial. The failures are systemic:
provider and consumer surfaces have no versioned compatibility contract,
upgrades can leave the wheel, state, projections, prompt, and specs schema at
different versions, and the consumer starts fresh root-level Codex executions
without deterministically injecting the selected Spec Context.

Release `v0.2.5` is the mandatory remediation release. Every finding below is
in scope and must be closed with automated evidence before closure.

## Findings and required dispositions

| Severity | Finding | Required disposition in v0.2.5 |
|---|---|---|
| CRITICAL | No versioned provider-consumer compatibility contract exists. | Publish a machine-readable capability contract and enforce it from Hermes and provider tests. |
| HIGH | Hermes upgrades only the persistent wheel. | Add transactional, exact-version reconciliation of package, state, public projections, doctors, and rollback behavior. |
| HIGH | Hermes prompt and tests preserve removed lifecycle commands. | Consume the installed version-matched skill/capability surface and test canonical workflow verbs. |
| HIGH | Fresh root-level `codex exec` tasks miss target-repository context. | Resolve an explicit context and inject its scoped rules, memory, active release, and current task into every run. |
| HIGH | Existing E2E does not certify the assembled consumer journey. | Add deterministic contract tests, persistent-upgrade E2E, empty-remote E2E, panel/doctor/scaffold/workflow certification, and a bounded live canary. |
| HIGH | The Hermes owning repository is governance-incoherent. | Restore one-task-at-a-time markers, valid memory/schema state, and immutable release evidence before certification. |
| MEDIUM | `context list --json` is documented but unsupported. | Implement and test stable JSON output. |
| MEDIUM | `context heartbeat` ignores the persisted bind. | Resolve caller-owned session identity without requiring a manually exported environment variable. |
| MEDIUM | Unbound context resolution selects the first ALIVE context. | Remove foreign-context fallback and fail with an actionable explicit-selection error. |
| MEDIUM | Empty repository onboarding has no explicit baseline contract. | Add operator-consented baseline initialization and an unborn-remote journey test. |
| MEDIUM | Telegram delivery truncates diagnostic output. | Deliver bounded chunks or persist and link the complete result without losing the failure cause. |
| MEDIUM | Academy notes are mistaken for executable agent knowledge. | Package versioned operational knowledge as an installed skill and keep Academy as evidence only. |

## Acceptance boundary

The release is not complete until a clean disposable workspace proves all
public feature families through supported interfaces: initialization,
Spec Context create/alive/dead/bind/heartbeat/list, scaffold and specs doctors,
public projections, all four lifecycle workflows, reports/handoffs, server
registry and panel smoke, capability discovery, upgrade reconciliation, and the
Hermes consumer bootstrap/task path.

Mocks may cover failure injection, but they cannot be the only evidence for
the assembled journey. Closure requires clean-room tests against built
artifacts and a bounded real-worker canary for every supported harness that is
available in CI or the release environment.

