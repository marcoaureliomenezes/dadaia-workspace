"""Agreement contract — the release-SemVer regex has ONE canonical home (v0.1.53 W3).

Before this release the literal ``re.compile(r"^v\\d+\\.\\d+\\.\\d+$")`` was triplicated
in three unrelated modules (``features/specs/scaffolder.py``,
``features/specs/doctor.py``, ``features/spec_artifacts/new_artifacts.py``) with no
shared constant and no test binding them together — a classic drift trap where one copy
could be tightened and the others silently rot.

FR3 centralises the pattern into ``core/specs_version.py`` as ``RELEASE_SEMVER_RE`` (+ the
``is_release_semver()`` helper) and repoints every consumer at it. This contract locks the
centralisation two ways, both decidable and free of false positives:

- **IDENTITY** — every consuming module resolves its canon reference to the *same*
  object the canon module defines (``is`` identity, not mere equality) — either
  ``RELEASE_SEMVER_RE`` itself (scaffolder.py, doctor_release.py, which still need the
  broader two-axis match for archive/naming lookups) or ``is_release_semver``
  (new_artifacts.py, which only ever MINTS and so only needs the bare-axis predicate).
  A re-introduced private copy would be a different object and fail here.
- **SCAN** — an AST walk of the production tree finds ``re.compile(<the semver
  pattern>)`` call sites; the only allowed site is the canon module. Message strings and
  docstrings that merely mention ``vX.Y.Z`` are excluded by construction — the scan only
  matches an actual ``re.compile`` call whose pattern argument equals the canonical
  pattern string.

AC-7(a) mutation-sanity: planting a competing ``re.compile`` copy anywhere in
``dadaia_workspace/`` makes the SCAN test fail (proven on the task line, then reverted).

**T-050-06A (SPEC FR1 boundary 2a / AS-13) flips the axis**: the canon widened to an
OPTIONAL ``v`` prefix — bare = the current, mintable axis; ``v``-prefixed = the retired
axis, matched only so an existing archived directory still resolves. The identity
assertion above stays green (canon still ONE compiled object); the BEHAVIOUR assertions
invert accordingly, under a recorded ``qa-engineer`` verdict — never deleted to go green.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

# The canonical release-SemVer pattern string. Held as a literal here (not imported) so
# the SCAN can run even while the canon is being established, and so a broken import of
# the canon fails as a clear assertion rather than a collection error.
# Widened 2026-07-19 (bug lifecycle-accepts-noncanonical-release-id retest): the ONE
# canon accepts an optional -suffix segment — rc/canary/hotfix release identities are
# legitimate at every public entry point (lifecycle verbs, release new, doctor).
# Widened again at T-050-06A (AS-13): the `v` prefix itself became OPTIONAL — bare is the
# current mintable axis, `v`-prefixed is the retired archive-only axis.
_SEMVER_PATTERN = r"^v?\d+\.\d+\.\d+(-[0-9A-Za-z][0-9A-Za-z.]*)?$"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PKG_ROOT = _REPO_ROOT / "dadaia_workspace"
#: The single module allowed to own the compiled pattern (repo-relative to _PKG_ROOT).
_CANON_REL = Path("core") / "specs_version.py"

#: Modules that must reuse the canon object, as (import path, attribute name) — the
#: attribute each module actually needs: the two naming/archive-lookup sites keep
#: RELEASE_SEMVER_RE (the broader two-axis match); the one MINT site (new_artifacts,
#: T-050-06A) needs only the narrower is_release_semver predicate.
#: v0.1.55 FR1: the SpecsDoctor RELEASE_SEMVER_RE consumer moved off the coordinator into the
#: ``doctor_release`` validator sibling (the SemVer/naming-canon checks live there now).
_CONSUMER_MODULES: tuple[tuple[str, str], ...] = (
    ("dadaia_workspace.features.specs.scaffolder", "RELEASE_SEMVER_RE"),
    ("dadaia_workspace.features.specs.doctor_release", "RELEASE_SEMVER_RE"),
    ("dadaia_workspace.features.spec_artifacts.new_artifacts", "is_release_semver"),
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
    py_paths = sorted(_PKG_ROOT.rglob("*.py"))
    # v0.4.5 FR5 (scan-test-vacuity-guard): a mis-rooted _PKG_ROOT would degrade this
    # walk to zero files, under which `offenders == []` below passes vacuously (the
    # IDENTITY checks above import the canon directly and would not catch it).
    assert_populated(py_paths, sentinel=_PKG_ROOT / _CANON_REL)
    offenders: list[str] = []
    for py_path in py_paths:
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
    from dadaia_workspace.core import specs_version as _canon_module

    for module_path, attr_name in _CONSUMER_MODULES:
        module = importlib.import_module(module_path)
        ref = getattr(module, attr_name, None)
        canon_attr = getattr(_canon_module, attr_name, None)
        assert ref is canon_attr and ref is not None, (
            f"{module_path}.{attr_name} must BE the canon object "
            f"(core.specs_version.{attr_name}), not a private copy"
        )

    offenders = _find_semver_compile_sites()
    assert offenders == [], (
        "release-SemVer pattern is re.compile()'d outside core/specs_version.py — "
        f"import RELEASE_SEMVER_RE from the canon instead. Offending sites: {offenders}"
    )

    from dadaia_workspace.core import specs_version

    is_release_semver = getattr(specs_version, "is_release_semver", None)
    assert callable(is_release_semver), "core.specs_version must define is_release_semver()"
    # AS-13/T-050-06A: is_release_semver is the MINT predicate — bare, current-axis
    # form ONLY. A `v`-prefixed id still matches the broader RELEASE_SEMVER_RE (it must
    # still resolve for archived-directory lookups, tested below) but is refused here.
    assert is_release_semver("0.1.53") is True
    assert is_release_semver("10.20.30") is True
    assert is_release_semver("1.2") is False
    assert is_release_semver("v0.1.53") is False
    assert is_release_semver("v10.20.30") is False
    # Suffixed identities are canonical since 2026-07-19 (rc/canary/hotfix flows).
    assert is_release_semver("1.2.3-rc1") is True
    assert is_release_semver("v1.2.3-rc1") is False
    assert is_release_semver("1.2.3-") is False
    assert is_release_semver("release-slug") is False

    # RELEASE_SEMVER_RE itself still matches BOTH axes (AS-13) — the object naming/
    # archive-lookup checks resolve against, never narrowed like the mint predicate.
    # (Re-imported typed here — `canon` above is `object` per `_canon_object()`'s
    # deliberately loose return type, so mypy --strict cannot narrow `.match` on it.)
    from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE as _typed_canon

    assert _typed_canon.match("0.1.53") is not None
    assert _typed_canon.match("v0.1.53") is not None
    assert _typed_canon.match("v1.2") is None
    assert _typed_canon.match("v1.2.3-") is None


def test_v_prefixed_release_id_refused_at_mint_but_archived_dir_still_resolves(
    tmp_path: Path,
) -> None:
    """A1.10: a fixture proves a new release id carrying a `v` prefix is refused at
    minting (`dadaia release new`), while an existing `v`-prefixed archived directory
    still resolves (`specs doctor`'s SPEC-DOC-016/SPEC-DOC-027 naming checks)."""
    from dadaia_workspace.features.spec_artifacts.new_artifacts import release_new
    from dadaia_workspace.features.specs import Severity, SpecsDoctor

    specs = tmp_path / "specs"
    specs.mkdir()

    # Half 1 — mint refusal: a v-prefixed id can never be created going forward.
    with pytest.raises(ValueError, match="Invalid release ID"):
        release_new(specs, "v0.9.9")
    assert not (specs / "releases" / "v0.9.9").exists()
    # The bare, current-axis form mints cleanly.
    result = release_new(specs, "0.9.9")
    assert (specs / "releases" / "0.9.9" / "SPEC.md").is_file()
    assert result.created is True

    # Half 2 — archive resolution: an EXISTING v-prefixed archived directory (the
    # retired axis, pre-canon-v6) is still recognised as conformant, never flagged.
    archived = specs / "_archive" / "releases" / "v0.4.4"
    archived.mkdir(parents=True)
    (archived / "SPEC.md").write_text(
        "**Status:** Aprovado\n**Created:** 2026-08-01\n", encoding="utf-8"
    )
    for fname in ("PLAN.md", "TASKS.md"):
        (archived / fname).write_text("x", encoding="utf-8")

    issues = SpecsDoctor(specs).check()
    naming_issues = [
        i
        for i in issues
        if i.code in ("SPEC-DOC-016", "SPEC-DOC-027") and i.severity == Severity.ERROR
    ]
    assert naming_issues == [], naming_issues
