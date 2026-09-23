---
slug: cross-platform-portability
title: cross-platform-portability
tldr: Linux, macOS and Windows through one platform capability seam, injected adapters, Python hooks and cross-OS CI legs.
summary: dadaia_workspace/core/platform.py is the single capability source and the container selects adapters; security failures are loud, non-security features degrade explicitly, unsupported critical capabilities fail at construction.
tags: [platform, cross-platform, portability, windows, macos, linux]
sources:
  - dadaia_workspace/core/platform.py
  - dadaia_workspace/infrastructure/file_permission_*.py
  - dadaia_workspace/infrastructure/signal_shutdown_*.py
  - dadaia_workspace/infrastructure/process_probe_adapter.py
  - dadaia_workspace/core/protocols/**
---

## Seam and validation

- The package imports and the CLI starts on Linux, macOS and Windows with no platform check scattered in feature code: `dadaia_workspace/core/platform.py` is the capability source and `dadaia_workspace/container.py` selects adapters.
- Two ports cover file permissions and shutdown, each with a POSIX and a Windows adapter under `dadaia_workspace/infrastructure/`; process probing is one adapter, `dadaia_workspace/infrastructure/process_probe_adapter.py`.
- No file lock exists anywhere: context and session state are coordinated without locking.
- Security controls fail loudly when a platform cannot provide them, non-security features degrade with an explicit log, and an unsupported critical capability fails at service construction.
- Harness governance hooks are Python modules invoked through per-harness wrappers; the git pre-push hook is a shell script and runs whatever the harness supports ([[sdd-gate-v3]]).
- Skill scripts are stdlib Python and degrade per host: the dev-server registry judges only TTL where no POSIX liveness probe exists ([[server-registry]]).
- CI runs Windows and macOS legs beside Linux; repository contracts refuse new unauthorized platform branches.

## Dependencies

[[workspace-init]], [[sdd-gate-v3]], [[ARCHITECTURE]], [[public-asset-distribution]], [[server-registry]].
