# Spec: Supported agent consumer certification - v0.2.5

> **Status:** Aprovado
> **Release ID:** v0.2.5
> **Owner:** product-engineer
> **Created:** 2026-07-15

## Problem

dadaia-workspace is intended to be the operating environment for humans and
agents, but a real Hermes consumer exposed gaps that isolated provider tests do
not catch. Provider wheels, workspace state, public projections, persisted
prompts, and specs schemas can drift independently. Agent consumers can invoke
obsolete commands, select the wrong context, miss nested rules and memory, or
fail inside a lifecycle worker sandbox while the outer command reports only a
generic artifact failure.

The complete source audit is
`specs/audits/2026-07-15-hermes-dadaia-integration.md`. This release is its
mandatory remediation release. No audit finding is accepted or deferred.

## Product contract

### Capability discovery

The installed runtime SHALL expose one machine-readable, versioned capability
document describing its public CLI groups, Spec Context operations, four
lifecycle workflows, specs standard version, public projection version, panel
and server surfaces, report/handoff contract, and compatibility requirements.
Agent prompts and tests SHALL consume this document instead of preserving copied
command syntax.

### Caller-owned context

- `context list --json` SHALL return stable structured output.
- `context heartbeat` SHALL resolve the current session's persisted bind when
  `DADAIA_SESSION_ID` is not manually exported.
- Unbound resolution SHALL never select an arbitrary first-ALIVE context.
- Failure SHALL name the exact explicit bind/context command needed to proceed.

### Transactional runtime reconciliation

A supported reconciliation operation SHALL verify an exact candidate version,
migrate state, stage and install all public projections, run public/workspace
doctors and a capability canary, and only then report promotion success. A
failed candidate SHALL leave an actionable diagnosis and SHALL NOT claim that
the workspace is upgraded.

### Empty repository onboarding

Context onboarding SHALL distinguish materialization from creation of an
initial Git baseline. An explicit, operator-consented command/flag SHALL create
the scaffold baseline for an unborn repository. Normal `alive` SHALL remain
non-committing and non-destructive.

### Lifecycle worker execution

Every real worker dispatch SHALL preflight executable availability, writable
artifact storage, and harness sandbox compatibility before model work begins.
Launch failures SHALL retain the root diagnostic and an operator command; an
exit-zero model response without required artifact evidence SHALL never be
described as a semantic workflow rejection.

### Full-capability certification

The project SHALL ship a deterministic certification entrypoint usable by
Hermes and other agents in a disposable workspace. It SHALL exercise supported
interfaces for:

- workspace initialization and exact-version reconciliation;
- specs scaffold/templates and specs doctor;
- context create, alive, list, bind, heartbeat, explicit switching, dead, and
  empty-remote baseline behavior;
- public stage/install/doctor and projected Codex/PI structures;
- all four lifecycle workflows and their state, artifact, block, resume, and
  evidence contracts;
- panel HTTP smoke and server registry lifecycle;
- report/handoff emission and validation;
- capability discovery and version-matched operational skill loading.

The deterministic suite may use fixture workers for repeatability, but closure
also requires bounded real Codex and PI canaries when those harnesses are
available. The Hermes repository SHALL run the provider contract against the
built candidate and its own bootstrap/task path before either release is
certified.

### Complete diagnostics

Consumer delivery SHALL preserve the full result through bounded message chunks
or a validated artifact reference. Truncating to the final tail is not compliant.

## Compatibility and migration

The release preserves existing human-readable commands. New JSON contracts are
additive and versioned. Removal of first-ALIVE fallback is an intentional safety
correction: automation must bind or pass a context explicitly. Upgrade scripts
that use `latest` must resolve it to an exact candidate before reconciliation.

## Security and credential boundary

Certification uses disposable repositories and workspace-root `.env` only.
It must never copy, print, persist, or attach credential values. Worker
diagnostics redact environment payloads and authentication material.

## Rollback

Revert the v0.2.5 implementation commit and reinstall the last certified exact
version. Re-run its matching projection install. Do not retain v0.2.5 prompts or
capability assertions against an older wheel.

## Acceptance criteria

- [ ] Every finding in the audit has a terminal implementation and test disposition.
- [ ] Every reported open bug named by this release has a resolving event with evidence.
- [ ] Provider unit, integration, feature E2E, and clean-room built-wheel certification pass.
- [ ] Real Codex and PI lifecycle canaries pass or closure explicitly proves a harness is unavailable rather than silently substituting a fake.
- [ ] Hermes executes the published full-capability script against the built candidate with zero failed checks and returns complete feedback.
- [ ] Specs/public/workspace doctors and repository hygiene checks have zero errors.

