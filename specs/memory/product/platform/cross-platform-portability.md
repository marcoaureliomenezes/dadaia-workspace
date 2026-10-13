---
slug: cross-platform-portability
title: cross-platform-portability
tldr: Linux, macOS and Windows through one platform capability seam carrying the venv layout, Python hooks and cross-OS CI legs.
summary: dadaia_workspace/core/platform.py is the package's one platform seam over the kernel's one host reader — the venv scripts directory, the executable suffix and the Windows path flavor, plus the one venv-executable rule; no port, adapter pair or file lock exists for portability.
tags: [platform, cross-platform, portability, windows, macos, linux]
sources:
  - dadaia_workspace/core/platform.py
---

## Seam and validation

- The package imports and the CLI starts on Linux, macOS and Windows with no platform check scattered in feature code: `dadaia_workspace/core/platform.py` is the package's capability source, and the kernel's `dd-bug-resolution/scripts/_platform.py` is the one `sys.platform` read, shared by the package and every skill script ([[bug-ledger]]).
- Its `PLATFORM` singleton carries `venv_scripts_dir` (`bin`, or `Scripts` on Windows), `venv_exe_suffix` (empty, or `.exe` on Windows) and `windows` (the host spells paths the Windows way); `venv_tool(venv, tool)` is the one rule for where a venv keeps an executable, used by the package (`core/cli_line.py`, `core/workspace_layout.py`) and the skill scripts alike, and `infrastructure/python_env.py` and the workspace doctor read the singleton ([[workspace-init]]).
- Every fix line naming the workspace CLI is spelled by `core/cli_line.py`: `shlex` quoting on POSIX; on Windows forward slashes and double quotes only around a blank, the one form Git Bash, cmd and PowerShell all run, proven by executing a printed line in each on the Windows CI leg; a workspace path holding a blank needs PowerShell's `& ` prefix ([[sdd-gate-v3]]).
- Portability needs no port and no adapter pair: `container.py` selects nothing per platform, and no file lock exists anywhere — context and session state are coordinated without locking.
- `core` imports no OS primitive (`fcntl`, `signal`, `subprocess`, `msvcrt`); the import-linter contract `core-no-os-primitives` measures it ([[ARCHITECTURE]] P-03).
- Harness governance hooks are Python modules invoked through per-harness wrappers; the git pre-push hook is a shell script and runs whatever the harness supports ([[sdd-gate-v3]]).
- Skill scripts are stdlib Python and degrade per host: the dev-server registry judges only TTL where no POSIX liveness probe exists ([[server-registry]]).
- CI runs Windows and macOS legs beside Linux, and `pyproject.toml` declares exactly those three OS classifiers.

## Dependencies

[[workspace-init]], [[sdd-gate-v3]], [[ARCHITECTURE]], [[public-asset-distribution]], [[server-registry]].
