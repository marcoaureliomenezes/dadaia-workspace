"""Bash-hook residue contract (WS-R6 / AC-R6-01, release v0.1.10).

Decision D-1 retired the bash hook quartet — ``sdd-spec-gate.sh``, ``sdd-post-gate.sh``,
``root-whitelist-gate.sh``, ``ctx-inject.sh``. The enforced gate is the Python hook package
``dadaia_workspace.hooks`` (``sdd_gate`` / ``sdd_post_gate`` / ``root_whitelist`` /
``ctx_inject``), wired as ``<python> -m dadaia_workspace.hooks.<name>`` on every harness.
Only ``pre-push-ci-gate.sh`` (a real git hook, deliberately shell) is kept.

This contract pins the retirement so it cannot silently regress:

1. :func:`test_quartet_absent_from_public_scripts` — the four ``.sh`` files are absent from
   the canonical asset tree ``dadaia_workspace/public/scripts/`` (AC-R6-01: "absent from
   canonical assets"), and ``pre-push-ci-gate.sh`` is still present.

2. :func:`test_no_code_ships_or_invokes_the_quartet` — no Python source under
   ``dadaia_workspace/`` references a retired script as a *shippable / invocable artifact*:
   no ``public/scripts/<name>.sh`` path, no ``bash .../<name>.sh`` invocation, no
   ``scripts``-dir ``<name>.sh`` filesystem target. Bare lineage/cleanup mentions are NOT
   residue: the ``ctx-inject.sh`` literal in ``features/workspace/service.py`` exists solely
   to DETECT-AND-REMOVE a stale legacy hook entry from a pre-existing workspace's
   ``settings.json`` — keeping it is part of finishing the retirement, not undoing it.

The grep is scoped to code + the public asset tree only. CHANGELOG, ``specs/``, and audit
history may mention the retired names freely.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_SCRIPTS = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts"
_CODE_ROOT = _REPO_ROOT / "dadaia_workspace"

RETIRED_SCRIPTS = (
    "sdd-spec-gate.sh",
    "sdd-post-gate.sh",
    "root-whitelist-gate.sh",
    "ctx-inject.sh",
)

# Patterns that mean a retired script is being SHIPPED or INVOKED as an artifact, as opposed
# to a bare lineage/cleanup mention. Any match is a hard residue failure.
_INVOCATION_PATTERNS = tuple(
    re.compile(p)
    for name in RETIRED_SCRIPTS
    for p in (
        # path into the public asset tree, e.g. public/scripts/sdd-spec-gate.sh
        rf"scripts['\"/]+\s*[/)]*\s*['\"]?{re.escape(name)}",
        rf"public/scripts/{re.escape(name)}",
        # shelling out to the script, e.g. bash .../sdd-spec-gate.sh
        rf"bash[^\n]*{re.escape(name)}",
    )
)


def _python_sources(root: Path) -> list[Path]:
    return [p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts]


def test_quartet_absent_from_public_scripts() -> None:
    """The four retired hook scripts are gone; pre-push-ci-gate.sh remains."""
    present = {p.name for p in _PUBLIC_SCRIPTS.glob("*.sh")}
    leaked = present.intersection(RETIRED_SCRIPTS)
    assert not leaked, f"retired bash hook(s) still in public/scripts/: {sorted(leaked)}"
    assert "pre-push-ci-gate.sh" in present, (
        "pre-push-ci-gate.sh must be retained (Decision D-1: kept git hook)"
    )
    # S-1: no compiled-bytecode artifact is git-tracked under public/scripts/. The dir
    # may hold a transient __pycache__ (siblings are real .py scripts Python compiles on
    # import); the invariant is that none of it is committed to the canonical asset tree.
    tracked = subprocess.run(
        ["git", "ls-files", "dadaia_workspace/public/scripts/"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    committed_bytecode = [p for p in tracked if "__pycache__" in p or p.endswith((".pyc", ".pyo"))]
    assert not committed_bytecode, (
        f"compiled bytecode committed under public/scripts/ (S-1): {committed_bytecode}"
    )


def test_no_code_ships_or_invokes_the_quartet() -> None:
    """No Python source references a retired script as a shippable/invocable artifact."""
    offenders: list[str] = []
    for src in _python_sources(_CODE_ROOT):
        rel = src.relative_to(_REPO_ROOT).as_posix()
        for lineno, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
            if any(pat.search(line) for pat in _INVOCATION_PATTERNS):
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "retired bash hook quartet still shipped/invoked from code:\n" + "\n".join(offenders)
    )
