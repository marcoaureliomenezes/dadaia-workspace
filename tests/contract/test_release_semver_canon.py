"""Intent: CONTRACT — core.specs_version RELEASE_SEMVER_RE single canon (DADAIA §4.2 no v prefix)

Agreement contract — the release-SemVer regex has ONE canonical home (v0.1.53 W3).

Before this release the literal ``re.compile(r"^v\\d+\\.\\d+\\.\\d+$")`` was triplicated
in three unrelated modules (``features/specs/scaffolder.py``,
``features/specs/doctor.py``, the retired ``features/spec_artifacts/new_artifacts.py`` (now ``features/specs/canon.py``)) with no
shared constant and no test binding them together — a classic drift trap where one copy
could be tightened and the others silently rot.

FR3 centralises the pattern into ``core/specs_version.py`` as ``RELEASE_SEMVER_RE`` (+ the
``is_release_semver()`` helper) and repoints every consumer at it. This contract locks the
centralisation two ways, both decidable and free of false positives:

- **IDENTITY** — every consuming module resolves its canon reference to the *same*
  object the canon module defines (``is`` identity, not mere equality) — either
  ``RELEASE_SEMVER_RE`` itself (scaffolder.py, doctor_release.py, which still need the
  broader two-axis match for archive/naming lookups) or ``is_release_semver``
  (features.specs.canon, which only ever MINTS and so only needs the bare-axis predicate).
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
#: RELEASE_SEMVER_RE (the broader two-axis match); the MINT site is the release skill
#: script (0.4.7 T-047-66), stdlib-only and outside this package scan;
#: T-050-06A) needs only the narrower is_release_semver predicate.
#: v0.1.55 FR1: the SpecsDoctor RELEASE_SEMVER_RE consumer moved off the coordinator into the
#: ``doctor_release`` validator sibling (the SemVer/naming-canon checks live there now).
_CONSUMER_MODULES: tuple[tuple[str, str], ...] = (
    ("dadaia_workspace.features.specs.scaffolder", "RELEASE_SEMVER_RE"),
    ("dadaia_workspace.features.specs.doctor_release", "RELEASE_SEMVER_RE"),
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


def test_v_prefixed_archived_dir_still_resolves(tmp_path: Path) -> None:
    """A1.10, archive half: an existing `v`-prefixed archived directory still resolves
    as conformant (`specs doctor`'s SPEC-DOC-027 naming check —
    SPEC-DOC-016 no longer scans root specs/_archive/releases/ at all, v6 canon:
    that root retired, T-050-14 deleted its last content, so this fixture's
    SPEC-DOC-016 exemption is now moot by construction rather than by allowlist;
    SPEC-DOC-027's own allowlist is the check still meaningfully exercised here)."""
    from dadaia_workspace.features.specs import Severity, SpecsDoctor

    specs = tmp_path / "specs"
    specs.mkdir()

    # The mint-refusal half moved with the minting verb (0.4.7 T-047-66):
    # `tests/unit/skills/test_release_implementation_release_script.py`.
    # An EXISTING v-prefixed archived directory (the
    # retired axis, pre-canon-v6) is still recognised as conformant, never flagged.
    archived = specs / "_archive" / "releases" / "v0.4.4"
    archived.mkdir(parents=True)
    (archived / "SPEC.md").write_text(
        "**Status:** Approved\n**Created:** 2026-08-01\n", encoding="utf-8"
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


# ---------------------------------------------------------------------------
# release-please canon — the manifest floor and the pre-1.0 bump flags
# ---------------------------------------------------------------------------

_MANIFEST_PATH = _REPO_ROOT / ".release-please-manifest.json"
_CONFIG_PATH = _REPO_ROOT / "release-please-config.json"


def _published_tags() -> list[str]:
    """Every ``v*`` tag reachable in this checkout, newest last (version order).

    CI checks this repository out shallow and without tags, so an empty list is a
    legitimate environment, not a failure — the caller skips on it.
    """
    import subprocess

    result = subprocess.run(
        ["git", "tag", "-l", "v*", "--sort=version:refname"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_release_please_manifest_sits_at_the_last_published_version() -> None:
    """The manifest is release-please's floor: it must name the last PUBLISHED
    version, so the first release PR proposes the next one rather than re-minting a
    version that already carries a tag."""
    import json

    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert set(manifest) == {"."}, f"the manifest addresses one package, the root: {manifest}"
    version = manifest["."]
    from dadaia_workspace.core.specs_version import is_release_semver

    assert isinstance(version, str) and is_release_semver(version), (
        f"the manifest version must be a bare SemVer (no `v` prefix): {version!r}"
    )

    import tomllib

    minted = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
        "poetry"
    ]["version"]
    assert minted == version, (
        f"pyproject.toml mints {minted!r} but the release-please manifest floor is "
        f"{version!r} — release-please reads the manifest and expects pyproject to "
        "agree; the two move together, in one bot-authored commit (D10, T-047-90)"
    )

    tags = _published_tags()
    if not tags:
        pytest.skip("no v* tags in this checkout (shallow CI clone) — floor unverifiable here")
    assert f"v{version}" == tags[-1], (
        f"the manifest floor must equal the latest published tag {tags[-1]!r}, got v{version}"
    )


def test_release_please_config_mints_a_patch_below_one_point_zero() -> None:
    """Pre-1.0, release-please bumps the MINOR on a `feat` unless both flags are set.
    The project mints patch releases from `feat` commits, so both must be true."""
    import json

    config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    assert config.get("bump-minor-pre-major") is True
    assert config.get("bump-patch-for-minor-pre-major") is True
    assert config.get("include-component-in-tag") is False, (
        "tags are bare `v<version>` — a component prefix would break every tag consumer"
    )

    root_package = config["packages"]["."]
    assert root_package["release-type"] == "python", (
        "the release type lives in the config's root package, never as an action input "
        f"(a `release-type:` input switches the action out of manifest mode): {root_package}"
    )
    assert root_package["changelog-path"] == "CHANGELOG.md"

    sections = {entry["type"]: entry for entry in config["changelog-sections"]}
    assert {"feat", "fix", "refactor", "docs", "ci", "test", "chore"} <= set(sections)
    for commit_type, entry in sections.items():
        assert entry["section"], f"section {commit_type} must carry a heading"
        assert isinstance(entry["hidden"], bool)
