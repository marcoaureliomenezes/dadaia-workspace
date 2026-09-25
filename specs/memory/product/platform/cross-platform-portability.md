---
slug: cross-platform-portability
title: cross-platform-portability
tldr: Linux, macOS and Windows through one platform capability seam carrying the venv layout, Python hooks and cross-OS CI legs.
summary: dadaia_workspace/core/platform.py is the single capability source — two flags, the venv scripts directory and the executable suffix — read by the modules that build venv paths; no port, adapter pair or file lock exists for portability.
tags: [platform, cross-platform, portability, windows, macos, linux]
sources:
  - dadaia_workspace/core/platform.py
---

## Seam and validation

- The package imports and the CLI starts on Linux, macOS and Windows with no platform check scattered in feature code: `dadaia_workspace/core/platform.py` is the capability source and the one `sys.platform` read.
- Its `PLATFORM` singleton carries two capabilities, `venv_scripts_dir` (`bin`, or `Scripts` on Windows) and `venv_exe_suffix` (empty, or `.exe` on Windows); the modules that build a venv executable path (`infrastructure/python_env.py`, `infrastructure/runtime_config.py`) read them ([[workspace-init]]).
- Portability needs no port and no adapter pair: `container.py` selects nothing per platform, and no file lock exists anywhere — context and session state are coordinated without locking.
- `core` imports no OS primitive (`fcntl`, `signal`, `subprocess`, `msvcrt`); the import-linter contract `core-no-os-primitives` measures it ([[ARCHITECTURE]] P-03).
- Harness governance hooks are Python modules invoked through per-harness wrappers; the git pre-push hook is a shell script and runs whatever the harness supports ([[sdd-gate-v3]]).
- Skill scripts are stdlib Python and degrade per host: the dev-server registry judges only TTL where no POSIX liveness probe exists ([[server-registry]]).
- CI runs Windows and macOS legs beside Linux, and `pyproject.toml` declares exactly those three OS classifiers.

## Dependencies

[[workspace-init]], [[sdd-gate-v3]], [[ARCHITECTURE]], [[public-asset-distribution]], [[server-registry]].
