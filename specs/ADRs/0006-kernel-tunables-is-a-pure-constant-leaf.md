# ADR 0006 — `core.kernel_tunables` is a pure-constant leaf

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Lifecycle timing constants (timeouts, throttles, staleness windows) were previously restated
in more than one place, so a tuned value in one caller silently disagreed with another. The
fix was a single home, `core.kernel_tunables` (DP-1). Because hooks, features and the CLI all
hold a legal edge to that module, a single import *from* it into any upper layer would create
a cycle touching every ring at once — and, being a constants module, it is exactly the file
where such an import would look harmless.

## Decision
We will keep `core.kernel_tunables` a pure-constant leaf: it is the single home for lifecycle
timing constants and imports no `features`, `infrastructure`, `cli` or `hooks` module. A
tunable that needs computation belongs to its caller, not to the leaf.

## Consequences
+ One number per tunable, importable from the hot path (a hook) without pulling any graph.
+ The narrowed contract reports a stray edge with a precise, actionable message rather than
  the whole-`core` message ADR 0004 would emit.
− A tunable whose value depends on runtime state cannot live here; it must be resolved by the
  caller and passed down.

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract
`kernel-tunables-is-a-leaf` (zero `ignore_imports`).
