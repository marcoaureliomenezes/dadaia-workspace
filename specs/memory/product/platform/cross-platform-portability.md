---
slug: cross-platform-portability
title: cross-platform-portability
category: product
tldr: Linux, macOS, and Windows support through a single platform capability seam, injected adapters, Python hooks, and hard-gated cross-OS tests.
summary: >-
  `core/platform.py` owns platform detection. OS-sensitive behavior is behind ports and
  infrastructure adapters; security failures are loud, non-security features degrade
  explicitly, and unsupported capabilities fail at construction.
tags:
- platform
- cross-platform
- portability
- windows
- macos
- linux
token_estimate: 213
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

The package imports and the CLI starts on Linux, macOS, and Windows. Feature code does
not scatter platform checks; `core/platform.py` is the capability source and
`container.py` selects adapters.

## Adapter Boundaries

Ports cover telemetry refresh serialization, file permissions, process probing,
process ancestry, and shutdown handling. Infrastructure supplies POSIX/Windows
implementations. Workspace/Spec Context coordination itself has no file-lock port.

Security controls fail loudly when a platform cannot provide them. Non-security
features may degrade with an explicit log and bounded behavior. Unsupported critical
capabilities fail during service construction.

## Hooks

Harness governance hooks are Python modules. Kimi Code invokes them through user-level
TypeScript extension. Git chokepoints remain shell scripts because Git for Windows
ships a compatible shell: `pre-commit-presence-gate.sh` and `pre-push-ci-gate.sh`.

## Validation

CI hard-gates Windows/macOS importability plus unit/contract subsets. Linux runs the
integration and browser suites that depend on local process/network facilities.
Repository contracts prevent new unauthorized `sys.platform`, `fcntl`, or adapter
construction sites.

## Dependencies

[[workspace-init]], [[sdd-gate-v3]], [[architecture]], [[multi-platform-parity]].
