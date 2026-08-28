---
slug: cross-platform-portability
title: cross-platform-portability
category: product
tldr: Linux, macOS and Windows through one platform capability seam, injected adapters, Python hooks and hard-gated cross-OS CI legs.
summary: "`core/platform.py` is the single capability seam and `container.py` selects adapters; security failures are loud, non-security features degrade explicitly, and unsupported capabilities fail at construction."
tags:
- platform
- cross-platform
- portability
- windows
- macos
- linux
---

## Seam and validation

The package imports and the CLI starts on Linux, macOS and Windows. Feature code scatters no
platform checks: `core/platform.py` (`Capabilities`, `detect()`) is the capability source and
`container.py` selects adapters. Ports cover telemetry refresh serialization, file permissions,
process probing, process ancestry and shutdown handling, with POSIX and Windows implementations in
`infrastructure/`; Spec Context coordination itself has no file-lock port. Security controls fail
loudly when a platform cannot provide them, non-security features may degrade with an explicit log
and bounded behavior, and an unsupported critical capability fails during service construction.

Canonical assets originate under `dadaia_workspace/public/` and project to each runtime's native
surface, honest about differing primitives ([[public-asset-distribution]], [[harness-claude-code]],
[[harness-codex]], [[harness-kimi-code]]). Harness governance hooks are Python modules invoked
through per-harness wrappers or shims; the git chokepoints stay shell scripts and run regardless of
harness hook support, because Git for Windows ships a compatible shell ([[sdd-gate-v3]]).

CI hard-gates Windows/macOS importability plus unit and contract subsets; Linux runs the integration
and browser suites that need local process and network facilities. Repository contracts refuse new
unauthorized `sys.platform`, `fcntl` or adapter construction sites.

## Dependencies

[[workspace-init]], [[sdd-gate-v3]], [[architecture]].
