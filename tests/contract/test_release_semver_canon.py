"""Agreement contract — the release-SemVer regex has ONE canonical home (v0.1.53 W3).

Before this release the literal ``re.compile(r"^v\\d+\\.\\d+\\.\\d+$")`` was triplicated
in three unrelated modules (``features/specs/scaffolder.py``,
``features/specs/doctor.py``, ``features/spec_artifacts/new_artifacts.py``) with no
shared constant and no test binding them together — a classic drift trap where one copy
could be tightened and the others silently rot.

FR3 centralises the pattern into ``core/specs_version.py`` as ``RELEASE_SEMVER_RE`` (+ the
``is_release_semver()`` helper) and repoints every consumer at it. This contract locks the
centralisation two ways, both decidable and free of false positives:

- **IDENTITY** — every consuming module resolves ``RELEASE_SEMVER_RE`` to the *same
  compiled object* the canon module defines (``is`` identity, not mere equality). A
  re-introduced private copy would be a different object and fail here.
- **SCAN** — an AST walk of the production tree finds ``re.compile(<the semver
  pattern>)`` call sites; the only allowed site is the canon module. Message strings and
  docstrings that merely mention ``vX.Y.Z`` are excluded by construction — the scan only
  matches an actual ``re.compile`` call whose pattern argument equals the canonical
  pattern string.

AC-7(a) mutation-sanity: planting a competing ``re.compile`` copy anywhere in
``dadaia_workspace/`` makes the SCAN test fail (proven on the task line, then reverted).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

# The canonical release-SemVer pattern string. Held as a literal here (not imported) so
# the SCAN can run even while the canon is being established, and so a broken import of
# the canon fails as a clear assertion rather than a collection error.
_SEMVER_PATTERN = r"^v\d+\.\d+\.\d+$"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PKG_ROOT = _REPO_ROOT / "dadaia_workspace"
#: The single module allowed to own the compiled pattern (repo-relative to _PKG_ROOT).
_CANON_REL = Path("core") / "specs_version.py"

#: Modules that must reuse the canon object, as (import path, attribute name).
#: v0.1.55 FR1: the SpecsDoctor RELEASE_SEMVER_RE consumer moved off the coordinator into the
#: ``doctor_release`` validator sibling (the SemVer/naming-canon checks live there now).
_CONSUMER_MODULES: tuple[str, ...] = (
    "dadaia_workspace.features.specs.scaffolder",
    "dadaia_workspace.features.specs.doctor_release",
    "dadaia_workspace.features.spec_artifacts.new_artifacts",
)


def _canon_object() -> object | None:
    """Return ``core.specs_version.RELEASE_SEMVER_RE`` or ``None`` if not yet defined."""
    from dadaia_workspace.core import specs_version

    return getattr(specs_version, "RELEASE_SEMVER_RE", None)


def _find_semver_compile_sites() -> list[str]:
    """AST-scan the production tree for ``re.compile(<semver pattern>)`` call sites.

    Returns ``["<rel-path>:<lineno>", ...]`` for every offending site OUTSIDE the canon
    module. Only a literal ``re.compile`` call whose first positional argument is a string
    constant equal to :data:`_SEMVER_PATTERN` counts — comments, docstrings, and help
    text that merely mention ``vX.Y.Z`` never match.
    """
    offenders: list[str] = []
    for py_path in sorted(_PKG_ROOT.rglob("*.py")):
        rel = py_path.relative_to(_PKG_ROOT)
        if rel == _CANON_REL:
            continue
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_re_compile = (
                isinstance(func, ast.Attribute)
                and func.attr == "compile"
                and isinstance(func.value, ast.Name)
                and func.value.id == "re"
            )
            if not (is_re_compile and node.args):
                continue
            first = node.args[0]
            if (
                isinstance(first, ast.Constant)
                and isinstance(first.value, str)
                and first.value == _SEMVER_PATTERN
            ):
                offenders.append(f"{rel.as_posix()}:{node.lineno}")
    return offenders


# ---------------------------------------------------------------------------
# IDENTITY — every consumer resolves the SAME compiled object
# ---------------------------------------------------------------------------


def test_release_semver_single_canon_identity_scan_and_behavior() -> None:
    """IDENTITY: canon defines RELEASE_SEMVER_RE and every consumer resolves the SAME
    compiled object. SCAN: no re.compile of the pattern outside the canon module.
    BEHAVIOUR: is_release_semver accepts the canon form and rejects near-misses."""
    import importlib

    canon = _canon_object()
    assert canon is not None, "core.specs_version must define RELEASE_SEMVER_RE (the canon)"
    assert getattr(canon, "pattern", None) == _SEMVER_PATTERN, (
        f"canon pattern must be {_SEMVER_PATTERN!r}, got {getattr(canon, 'pattern', None)!r}"
    )
    for module_path in _CONSUMER_MODULES:
        module = importlib.import_module(module_path)
        ref = getattr(module, "RELEASE_SEMVER_RE", None)
        assert ref is canon, (
            f"{module_path}.RELEASE_SEMVER_RE must BE the canon object "
            f"(core.specs_version.RELEASE_SEMVER_RE), not a private copy"
        )

    offenders = _find_semver_compile_sites()
    assert offenders == [], (
        "release-SemVer pattern is re.compile()'d outside core/specs_version.py — "
        f"import RELEASE_SEMVER_RE from the canon instead. Offending sites: {offenders}"
    )

    from dadaia_workspace.core import specs_version

    is_release_semver = getattr(specs_version, "is_release_semver", None)
    assert callable(is_release_semver), "core.specs_version must define is_release_semver()"
    assert is_release_semver("v0.1.53") is True
    assert is_release_semver("v10.20.30") is True
    assert is_release_semver("v1.2") is False
    assert is_release_semver("1.2.3") is False
    assert is_release_semver("v1.2.3-rc1") is False
    assert is_release_semver("release-slug") is False
