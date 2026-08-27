# ADR 0003 — `core` is OS-primitive free

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
`fcntl`, `msvcrt`, `signal` and `subprocess` are platform-divergent: a module-level import of
one of them fails outright on the platform that lacks it. This product has already paid that
bill — a top-level `fcntl` import inside a shared module broke every Windows run, which is
why the cross-platform compatibility work introduced a single platform seam. `core` is the
ring every other ring imports, so one OS primitive there makes the whole package
unimportable on the wrong platform. `core/platform.py` reads `sys` only and is that seam.

## Decision
We will keep `core` free of OS-primitive modules (`fcntl`, `signal`, `subprocess`, `msvcrt`);
`core/platform.py` is the sole platform-detection site, and platform-specific behaviour lives
behind an infrastructure adapter selected at the composition root.

## Consequences
+ Importing `core` is safe on every supported platform, so hooks and the CLI start the same
  way everywhere.
+ Platform divergence is confined to one named module plus adapters, which is where the
  cross-platform tests point.
− A `core` helper that needs a platform primitive must be pushed down to an adapter or
  expressed as a port, which costs an indirection.

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `core-no-os-primitives`
(zero `ignore_imports`; the `platform` seam's `sys` read is attribute access, not a forbidden
module import).
