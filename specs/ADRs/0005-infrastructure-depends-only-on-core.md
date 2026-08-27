# ADR 0005 — `infrastructure` depends only on `core`

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Adapters exist to satisfy ports. An adapter that reaches back up into a feature, the CLI or a
hook inverts that relation: the feature can no longer be tested against a fake, and two
features start sharing state through an adapter nobody reads as shared. This is the same
reverse-direction finding (A3) that pinned `core` as the bottom ring — `infrastructure` was
also verified to have zero upward edges, so the fact was frozen rather than remediated.

## Decision
We will let `infrastructure` depend on `core` only: an adapter imports ports, models and
helpers from `core` and never `dadaia_workspace.features`, `dadaia_workspace.cli` or
`dadaia_workspace.hooks`. Composition of an adapter with a feature happens in `container.py`.

## Consequences
+ Every adapter is substitutable in tests, because it depends only on the ring below it.
+ Two features cannot become coupled through an adapter's private reach into one of them.
− Data an adapter needs from a feature must be passed in by the caller or modelled in `core`,
  which occasionally makes a signature wider.

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract
`infrastructure-no-upper-layers` (zero `ignore_imports`).
