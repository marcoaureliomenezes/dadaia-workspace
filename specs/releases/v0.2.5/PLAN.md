# Plan: Supported agent consumer certification - v0.2.5

> **Status:** Aprovado
> **Release ID:** v0.2.5
> **Owner:** software-architect

## Implementation sequence

1. Correct caller-owned context resolution and add stable JSON context listing.
2. Publish a versioned capability manifest and expose it through the CLI.
3. Add exact-version workspace reconciliation with stage/install/doctor/canary postconditions.
4. Add explicit initial-baseline onboarding for unborn repositories.
5. Preflight lifecycle worker writability/sandbox execution and preserve root diagnostics.
6. Build a disposable full-capability certification runner and provider-side journeys.
7. Project a version-matched dadaia mastery skill and consumer compatibility guidance.
8. Run built-artifact, Hermes consumer, Codex, PI, panel, doctor, and hygiene gates; resolve every release bug and close.

## Architectural boundaries

- `features/*` owns use-case contracts; CLI commands remain adapters.
- Capability data has one canonical source and is projected, not duplicated.
- Reconciliation composes existing migration/public/doctor services; it does not shell through copied UI text.
- Certification creates all state under a disposable workspace in `.dadaia/tmp/`.
- No provider test imports or modifies the external Hermes working tree.
- Consumer compatibility is proven against a built wheel through a declared contract version.

## Validation Dependency Table

| Validation | Depends on | Evidence required |
|---|---|---|
| Context contract tests | T1 | JSON schema, persisted-bind heartbeat, unbound failure |
| Capability contract tests | T2 | CLI JSON validates canonical manifest |
| Upgrade/reconciliation journey | T2, T3 | candidate failure rollback and successful projection convergence |
| Empty-remote journey | T1, T4 | unborn remote to explicit baseline to alive/dead round trip |
| Real worker canary | T5 | writable preflight plus retained failure root cause |
| Full deterministic certification | T1-T7 | every public feature family reports PASS |
| Hermes assembled certification | T2, T3, T6, T7 plus consumer release | built-wheel bootstrap and task execution |
| Closure quality ladder | T1-T8 | unit, integration, E2E, doctors, panel, Codex, PI, hygiene |

## Risk controls

- Preserve human CLI compatibility while versioning all machine output.
- Use explicit opt-in for Git commits and destructive context transitions.
- Keep live-harness canaries bounded and separate from deterministic fixture runs.
- Fail closed on unknown capability contract versions.
- Never convert an unavailable live harness into a passing fake result.

