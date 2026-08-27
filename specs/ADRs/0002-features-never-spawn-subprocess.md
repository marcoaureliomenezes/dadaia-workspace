# ADR 0002 — Features never spawn a subprocess

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Process execution is the least portable and least testable surface in the product: a direct
`import subprocess` inside a feature drags shell quoting, exit-code handling and platform
divergence into feature logic, and forces every test of that feature to run a real process.
The audited defect was exactly that — features shelling out directly. The sanctioned
boundary is the `ProcessRunner` port with its infrastructure adapter; three lazy adapter
fallbacks (`server_registry.scan`, `ci_preflight.service`, `import_.service`) remain declared
debt, and one former edge (`doctor_memory`) was removed outright when the check stopped
shelling out at all.

## Decision
We will never import `subprocess` from a feature: process execution goes through the
`ProcessRunner` port, injected from the container, with the infrastructure adapter as the
single sanctioned crossing.

## Consequences
+ Feature tests substitute a fake runner instead of spawning processes, which keeps the unit
  tier fast and hermetic.
+ Quoting, environment and exit-code handling live in one adapter, so a fix there fixes every
  caller.
− The three lazy fallback edges are counted against the ignore-edge cap (ADR 0010) until
  container DI reaches those call sites.
− A feature that genuinely needs a new process capability must extend the port first, which is
  slower than calling `subprocess` inline — deliberately.

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `features-no-subprocess`
(3 declared `ignore_imports`, the adapter edges that break the transitive chain).
