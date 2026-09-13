---
slug: cross-platform-portability
title: cross-platform-portability
tldr: Linux, macOS and Windows through one platform capability seam, injected adapters, Python hooks and hard-gated cross-OS CI legs.
summary: core/platform.py is the single capability seam and the container selects adapters; security failures are loud, non-security features degrade explicitly, unsupported capabilities fail at construction.
tags: [platform, cross-platform, portability, windows, macos, linux]
---

## Seam and validation

- The package imports and the CLI starts on Linux, macOS and Windows, with no platform check scattered in feature code: `core/platform.py` (`Capabilities`, `detect()`) is the capability source and `container.py` selects adapters.
- Three ports cover telemetry refresh serialization, file permissions and shutdown, each with a POSIX and a Windows adapter in `infrastructure/`; process probing is one adapter (`process_probe_adapter.py`) imported directly by its consumer, and no ancestry seam exists.
- Spec Context coordination itself has no file-lock port.
- Security controls fail loudly when a platform cannot provide them, non-security features degrade with an explicit log, and an unsupported critical capability fails at service construction.
- Harness governance hooks are Python modules invoked through per-harness wrappers or shims, while the git chokepoints stay shell scripts and run regardless of harness hook support ([[sdd-gate-v3]]).
- CI hard-gates Windows/macOS importability plus unit and contract subsets, Linux running the integration and browser suites; repository contracts refuse new unauthorized `sys.platform`, `fcntl` or adapter construction sites.

## Dependencies

[[workspace-init]], [[sdd-gate-v3]], [[ARCHITECTURE]], [[public-asset-distribution]].
