#!/usr/bin/env python3
"""Thin wrapper over the package's memory-atom lint (v0.4.3 T-043-20/FR16, A16.1/A16.2).

This script is no longer the canonical LINT-1 implementation. The lint logic — heading
allowlist, frontmatter-schema validation, wikilink resolution, the whole per-atom check
set — lives in ``dadaia_workspace.features.specs.memory_lint``, imported directly by
``features/specs/doctor_memory.py`` (no subprocess, no dependency on this projected copy
existing or being byte-identical to the package). This file is kept only as a standalone
CLI entry point — for a bare invocation (``python lint-memory-atoms.py --memory-dir
...``) in a workspace where the ``dadaia-workspace`` package is installed in the running
interpreter — that imports the package's ``main()`` and forwards its exit code, so the
CLI surface (the ``--memory-dir`` flag, exit codes 0/1/2) stays exactly what it was.

Usage:
    lint-memory-atoms.py [--memory-dir <path>]

    Default --memory-dir resolves to specs/memory relative to the workspace root
    found by walking up from CWD until a directory containing specs/memory is found
    (see ``memory_lint._resolve_default_memory_dir``).

Exit codes:
    0  — all atoms valid (no ERRORs, no WARNINGs)
    1  — at least one ERROR found
    2  — warnings only (no ERRORs, at least one WARNING)
"""

from __future__ import annotations

import sys

# Public-source hygiene (T-011-15 / FR-W5-01): never write a __pycache__/*.pyc under
# dadaia_workspace/public/. This guard fires no matter how the script is invoked
# (direct `python <script>`, subprocess, or import), complementing the `-B` flag at
# the subprocess call site in container.py's `_memory_lint_gate`.
sys.dont_write_bytecode = True

from dadaia_workspace.features.specs.memory_lint import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
