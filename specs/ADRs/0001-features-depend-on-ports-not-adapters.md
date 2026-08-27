# ADR 0001 — Features depend on ports, not adapters

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The package is a three-ring graph (`core` → `infrastructure` → `features`/`cli`/`hooks`).
A feature that imports a concrete adapter binds product logic to one store, one lock
implementation, one OS. The original lock-family audit found this layering was clean by
discipline only — nothing failed when an edge appeared — which is how the erosion started.
Seven suppressed edges survive today as documented, capped debt (two ADR-1 lazy telemetry
lock selections, three `ProcessRunner` fallbacks, one derived model-mapping data re-export,
one function-scoped rotation-helper edge in `chokepoints.service`); each carries a rationale
comment on the edge in `setup.cfg` and is counted by ADR 0010's cap.

## Decision
We will keep features on ports: a feature depends on `core.protocols` and the container
injects the concrete adapter; no feature imports `dadaia_workspace.infrastructure` directly.
A pre-existing suppressed edge is debt to be removed, never precedent for a new one — the
contract still fails on any NEW `features → infrastructure` import.

## Consequences
+ Adapters (store, lock, process, platform) are swappable at the composition root, and
  cross-platform substitution is a wiring decision instead of a code change inside a feature.
+ A new violation fails `lint-imports` in CI and in `dadaia ci preflight`, so the layering
  law stops depending on a reviewer noticing an import line.
− Constructor DI must be threaded through `container.py` for every new adapter need.
− The seven capped edges keep a visible, accounted debt until the DI cleanup lands; each
  costs one line of the ignore-edge cap (ADR 0010).

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract
`features-no-infrastructure` (7 declared `ignore_imports`, each with its reason line).
